"""Article assignment and version-bound acknowledgement tracking — this
phase's own instruction sections 9-10. Uses the Phase 10 task and
notification integration services rather than a parallel engine (this
phase's own instruction section 10: "Integrate with Phase 10 Operational
Tasks and Notifications rather than creating a parallel task engine").
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    KnowledgeAcknowledgement,
    KnowledgeArticle,
    KnowledgeAssignment,
    StaffUser,
    TaskRecord,
)
from app.knowledge.schemas import AssignmentCreateIn
from app.notifications.service import notify
from app.tasks.service import generate_task_number


async def create_assignment(
    session: AsyncSession,
    *,
    actor: StaffUser,
    article: KnowledgeArticle,
    payload: AssignmentCreateIn,
) -> KnowledgeAssignment:
    assignment = KnowledgeAssignment(
        article_id=article.id,
        version_id=payload.version_id,
        assignee_type=payload.assignee_type,
        staff_id=payload.staff_id,
        department_id=payload.department_id,
        role_id=payload.role_id,
        due_at=payload.due_at,
        is_mandatory=payload.is_mandatory,
        reason=payload.reason,
        assigned_by=actor.id,
    )
    session.add(assignment)
    await session.flush()

    if payload.assignee_type == "staff" and payload.staff_id is not None:
        # A stable operational task, not a new parallel tracking mechanism —
        # this phase's own instruction section 31: "Store stable references
        # back to the originating Phase 11 entity."
        session.add(
            TaskRecord(
                task_number=generate_task_number(),
                title=f"Acknowledge: {article.title}",
                description=payload.reason,
                source="system",
                priority="high" if payload.is_mandatory else "normal",
                status="open",
                due_at=payload.due_at,
                assigned_staff_id=payload.staff_id,
                related_type="knowledge_article",
                related_id=article.id,
                created_by=actor.id,
            )
        )
        await notify(
            session,
            notification_type="knowledge.assignment_created",
            title=f"New SOP assigned: {article.title}",
            record_type="knowledge_article",
            record_id=article.id,
            recipient_staff_id=payload.staff_id,
            dedup_key=f"knowledge.assigned:{article.id}:{payload.staff_id}",
        )
    await session.flush()
    return assignment


async def list_assignments(
    session: AsyncSession, article_id: uuid.UUID
) -> list[KnowledgeAssignment]:
    result = await session.scalars(
        select(KnowledgeAssignment).where(KnowledgeAssignment.article_id == article_id)
    )
    return list(result.all())


async def cancel_assignment(
    session: AsyncSession, *, assignment: KnowledgeAssignment
) -> KnowledgeAssignment:
    assignment.status = "cancelled"
    await session.flush()
    return assignment


async def record_view(
    session: AsyncSession, *, article: KnowledgeArticle, viewer: StaffUser
) -> KnowledgeAcknowledgement | None:
    """Opening a published article creates/updates its acknowledgement row
    for the current version, but never sets `acknowledged_at` — this
    phase's own instruction section 9: "Do not mark an article acknowledged
    merely because it was opened."""
    if article.published_version_id is None:
        return None
    now = datetime.now(UTC)
    ack = await session.scalar(
        select(KnowledgeAcknowledgement).where(
            KnowledgeAcknowledgement.article_id == article.id,
            KnowledgeAcknowledgement.version_id == article.published_version_id,
            KnowledgeAcknowledgement.staff_id == viewer.id,
        )
    )
    if ack is None:
        ack = KnowledgeAcknowledgement(
            article_id=article.id,
            version_id=article.published_version_id,
            staff_id=viewer.id,
            first_opened_at=now,
            last_opened_at=now,
            open_count=1,
        )
        session.add(ack)
    else:
        ack.last_opened_at = now
        ack.open_count += 1
        if ack.first_opened_at is None:
            ack.first_opened_at = now
    await session.flush()
    return ack


async def acknowledge_article(
    session: AsyncSession, *, article: KnowledgeArticle, staff: StaffUser
) -> KnowledgeAcknowledgement:
    if article.published_version_id is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This article has no published version to acknowledge."
        )
    version_id = article.published_version_id
    ack = await session.scalar(
        select(KnowledgeAcknowledgement).where(
            KnowledgeAcknowledgement.article_id == article.id,
            KnowledgeAcknowledgement.version_id == version_id,
            KnowledgeAcknowledgement.staff_id == staff.id,
        )
    )
    now = datetime.now(UTC)
    if ack is None:
        ack = KnowledgeAcknowledgement(
            article_id=article.id,
            version_id=version_id,
            staff_id=staff.id,
            first_opened_at=now,
            last_opened_at=now,
            open_count=1,
            acknowledged_at=now,
        )
        session.add(ack)
    else:
        ack.acknowledged_at = now
    await session.flush()

    assignment = await session.scalar(
        select(KnowledgeAssignment).where(
            KnowledgeAssignment.article_id == article.id,
            KnowledgeAssignment.assignee_type == "staff",
            KnowledgeAssignment.staff_id == staff.id,
            KnowledgeAssignment.status == "active",
        )
    )
    if assignment is not None:
        assignment.status = "completed"
    await session.flush()
    return ack


async def list_acknowledgements_for_article(
    session: AsyncSession, article_id: uuid.UUID
) -> list[KnowledgeAcknowledgement]:
    result = await session.scalars(
        select(KnowledgeAcknowledgement).where(KnowledgeAcknowledgement.article_id == article_id)
    )
    return list(result.all())
