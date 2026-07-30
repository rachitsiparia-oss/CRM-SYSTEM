"""Performance reviews and goals — this phase's own instruction section 25.
"Finalized reviews must not be silently edited" is a service-level guard:
once `finalized_at` is set, `update_review` refuses further edits.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PerformanceReview, PerformanceReviewGoal, StaffUser
from app.notifications.service import notify
from app.staff_operations.schemas import (
    PerformanceReviewCreateIn,
    PerformanceReviewUpdateIn,
)

REVIEW_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"in_progress"}),
    "in_progress": frozenset({"submitted"}),
    "submitted": frozenset({"reviewed", "in_progress"}),
    "reviewed": frozenset({"finalized"}),
    "finalized": frozenset({"acknowledged"}),
    "acknowledged": frozenset(),
}


def is_review_transition_allowed(current: str, target: str) -> bool:
    return target in REVIEW_TRANSITIONS.get(current, frozenset())


async def create_review(
    session: AsyncSession, *, actor: StaffUser, payload: PerformanceReviewCreateIn
) -> PerformanceReview:
    review = PerformanceReview(
        staff_user_id=payload.staff_user_id,
        reviewer_id=actor.id,
        cycle_label=payload.cycle_label,
        period_start_date=payload.period_start_date,
        period_end_date=payload.period_end_date,
        created_by=actor.id,
    )
    session.add(review)
    await session.flush()
    for goal in payload.goals:
        session.add(
            PerformanceReviewGoal(
                review_id=review.id,
                title=goal.title,
                description=goal.description,
                target_date=goal.target_date,
            )
        )
    await session.flush()
    return review


async def update_review(
    session: AsyncSession,
    *,
    actor: StaffUser,
    review: PerformanceReview,
    payload: PerformanceReviewUpdateIn,
) -> PerformanceReview:
    if review.version != payload.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This review was modified by someone else. Reload and try again.",
        )
    if review.finalized_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="A finalized review cannot be edited.")
    if payload.overall_rating is not None:
        review.overall_rating = payload.overall_rating
    if payload.strengths is not None:
        review.strengths = payload.strengths
    if payload.improvement_areas is not None:
        review.improvement_areas = payload.improvement_areas
    if payload.staff_comments is not None:
        review.staff_comments = payload.staff_comments
    if payload.manager_comments is not None:
        review.manager_comments = payload.manager_comments
    review.updated_by = actor.id
    review.version += 1
    await session.flush()
    return review


async def transition_review(
    session: AsyncSession, *, actor: StaffUser, review: PerformanceReview, target_status: str
) -> PerformanceReview:
    if not is_review_transition_allowed(review.status, target_status):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot move a review from {review.status!r} to {target_status!r}.",
        )
    review.status = target_status
    now = datetime.now(UTC)
    if target_status == "finalized":
        review.finalized_at = now
        review.finalized_by = actor.id
        await notify(
            session,
            notification_type="staff.review_finalized",
            title="Your performance review is ready",
            record_type="performance_review",
            record_id=review.id,
            recipient_staff_id=review.staff_user_id,
            dedup_key=f"staff.review_finalized:{review.id}",
        )
    if target_status == "acknowledged":
        review.staff_acknowledged_at = now
    await session.flush()
    return review


async def list_reviews(
    session: AsyncSession, staff_user_id: uuid.UUID | None
) -> list[PerformanceReview]:
    stmt = select(PerformanceReview)
    if staff_user_id:
        stmt = stmt.where(PerformanceReview.staff_user_id == staff_user_id)
    return list((await session.scalars(stmt)).all())


async def list_goals(session: AsyncSession, review_id: uuid.UUID) -> list[PerformanceReviewGoal]:
    result = await session.scalars(
        select(PerformanceReviewGoal).where(PerformanceReviewGoal.review_id == review_id)
    )
    return list(result.all())
