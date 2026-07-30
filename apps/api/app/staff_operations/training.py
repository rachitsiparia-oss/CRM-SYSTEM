"""Training courses, assignments, and attempts — this phase's own
instruction sections 21-22. "Prevent exceeding maximum attempts unless an
authorized reset occurs" is enforced against `TrainingCourse.max_attempts`
in `start_attempt`.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StaffUser, TrainingAssignment, TrainingAttempt, TrainingCourse
from app.notifications.service import notify
from app.staff_operations.schemas import (
    TrainingAssignIn,
    TrainingAttemptCompleteIn,
    TrainingCourseCreateIn,
)


async def create_course(
    session: AsyncSession, *, actor: StaffUser, payload: TrainingCourseCreateIn
) -> TrainingCourse:
    course = TrainingCourse(
        code=payload.code,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        department_id=payload.department_id,
        role_id=payload.role_id,
        is_mandatory=payload.is_mandatory,
        validity_period_days=payload.validity_period_days,
        passing_score=payload.passing_score,
        max_attempts=payload.max_attempts,
        content_source=payload.content_source,
        created_by=actor.id,
    )
    session.add(course)
    await session.flush()
    return course


async def list_courses(session: AsyncSession) -> list[TrainingCourse]:
    result = await session.scalars(select(TrainingCourse).where(TrainingCourse.is_active.is_(True)))
    return list(result.all())


async def assign_training(
    session: AsyncSession, *, actor: StaffUser, payload: TrainingAssignIn
) -> TrainingAssignment:
    existing = await session.scalar(
        select(TrainingAssignment).where(
            TrainingAssignment.course_id == payload.course_id,
            TrainingAssignment.staff_user_id == payload.staff_user_id,
        )
    )
    if existing is not None:
        existing.status = "assigned"
        existing.due_at = payload.due_at
        existing.assigned_by = actor.id
        await session.flush()
        assignment = existing
    else:
        assignment = TrainingAssignment(
            course_id=payload.course_id,
            staff_user_id=payload.staff_user_id,
            due_at=payload.due_at,
            assigned_by=actor.id,
            created_by=actor.id,
        )
        session.add(assignment)
        await session.flush()
    await notify(
        session,
        notification_type="staff.training_assigned",
        title="New training assigned",
        record_type="training_assignment",
        record_id=assignment.id,
        recipient_staff_id=payload.staff_user_id,
        dedup_key=f"staff.training_assigned:{assignment.id}",
    )
    await session.flush()
    return assignment


async def list_assignments(
    session: AsyncSession, *, staff_user_id: uuid.UUID | None, course_id: uuid.UUID | None
) -> list[TrainingAssignment]:
    stmt = select(TrainingAssignment)
    if staff_user_id:
        stmt = stmt.where(TrainingAssignment.staff_user_id == staff_user_id)
    if course_id:
        stmt = stmt.where(TrainingAssignment.course_id == course_id)
    return list((await session.scalars(stmt)).all())


async def start_attempt(
    session: AsyncSession, *, assignment: TrainingAssignment
) -> TrainingAttempt:
    course = await session.get(TrainingCourse, assignment.course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Course not found.")
    attempt_count = await session.scalar(
        select(func.count())
        .select_from(TrainingAttempt)
        .where(TrainingAttempt.assignment_id == assignment.id)
    )
    if (attempt_count or 0) >= course.max_attempts:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Maximum attempts ({course.max_attempts}) already used for this course.",
        )
    attempt = TrainingAttempt(
        assignment_id=assignment.id,
        attempt_number=(attempt_count or 0) + 1,
        started_at=datetime.now(UTC),
    )
    session.add(attempt)
    assignment.status = "in_progress"
    await session.flush()
    return attempt


async def complete_attempt(
    session: AsyncSession,
    *,
    actor: StaffUser,
    attempt: TrainingAttempt,
    assignment: TrainingAssignment,
    payload: TrainingAttemptCompleteIn,
) -> TrainingAttempt:
    course = await session.get(TrainingCourse, assignment.course_id)
    attempt.completed_at = datetime.now(UTC)
    attempt.score = payload.score
    attempt.completion_evidence = payload.completion_evidence
    attempt.reviewer_id = actor.id
    is_pass = (
        course is None or course.passing_score is None or payload.score >= course.passing_score
    )
    attempt.is_pass = is_pass
    assignment.status = "completed" if is_pass else "failed"
    await session.flush()
    return attempt


async def list_attempts(session: AsyncSession, assignment_id: uuid.UUID) -> list[TrainingAttempt]:
    result = await session.scalars(
        select(TrainingAttempt)
        .where(TrainingAttempt.assignment_id == assignment_id)
        .order_by(TrainingAttempt.attempt_number)
    )
    return list(result.all())
