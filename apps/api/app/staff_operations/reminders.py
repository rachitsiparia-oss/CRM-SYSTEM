"""Staff-operations reminder sweeps — certification expiry, overdue
training, and overdue knowledge acknowledgement. The underlying queries
(`list_certifications_expiring_within`, training/knowledge assignment
rows with a `due_at`) already existed from Phase 11; none of them were
ever wired to actually notify anyone before this phase (confirmed: zero
`notify()` call sites in either module previously). Training/knowledge
reminders dedup per calendar day (a still-overdue item nags again
tomorrow); certification reminders dedup per exact expiry date (a stable,
one-time-per-deadline signal, matching
INTEGRATIONS_AUTOMATIONS_REALTIME.md section 17.4's dedup examples).
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeAssignment, TrainingAssignment
from app.notifications.service import notify
from app.staff_operations.certifications import list_certifications_expiring_within

_CERTIFICATION_WARNING_DAYS = 30


async def dispatch_certification_expiry_reminders(
    session: AsyncSession, *, days: int = _CERTIFICATION_WARNING_DAYS
) -> int:
    expiring = await list_certifications_expiring_within(session, days=days)
    count = 0
    for cert in expiring:
        expiry_label = cert.expiry_date.isoformat() if cert.expiry_date else "none"
        result = await notify(
            session,
            notification_type="staff.certification.expiring",
            title=f"{cert.certification_type} is expiring soon",
            recipient_staff_id=cert.staff_user_id,
            body=f"Expires {expiry_label}.",
            record_type="staff_certification",
            record_id=cert.id,
            dedup_key=f"cert-expiring:{cert.id}:{expiry_label}",
        )
        if result is not None:
            count += 1
    return count


async def dispatch_training_overdue_reminders(
    session: AsyncSession, *, now: datetime | None = None
) -> int:
    now = now or datetime.now(UTC)
    overdue = (
        await session.scalars(
            select(TrainingAssignment).where(
                TrainingAssignment.status == "assigned",
                TrainingAssignment.due_at.isnot(None),
                TrainingAssignment.due_at <= now,
            )
        )
    ).all()
    count = 0
    for assignment in overdue:
        result = await notify(
            session,
            notification_type="staff.training.overdue",
            title="A training assignment is overdue",
            recipient_staff_id=assignment.staff_user_id,
            record_type="training_assignment",
            record_id=assignment.id,
            dedup_key=f"training-overdue:{assignment.id}:{now.date().isoformat()}",
        )
        if result is not None:
            count += 1
    return count


async def dispatch_knowledge_acknowledgement_reminders(
    session: AsyncSession, *, now: datetime | None = None
) -> int:
    now = now or datetime.now(UTC)
    overdue = (
        await session.scalars(
            select(KnowledgeAssignment).where(
                KnowledgeAssignment.status == "active",
                KnowledgeAssignment.assignee_type == "staff",
                KnowledgeAssignment.staff_id.isnot(None),
                KnowledgeAssignment.due_at.isnot(None),
                KnowledgeAssignment.due_at <= now,
            )
        )
    ).all()
    count = 0
    for assignment in overdue:
        if assignment.staff_id is None:
            continue
        result = await notify(
            session,
            notification_type="knowledge.assignment.overdue",
            title="A knowledge article acknowledgement is overdue",
            recipient_staff_id=assignment.staff_id,
            record_type="knowledge_article",
            record_id=assignment.article_id,
            dedup_key=f"knowledge-overdue:{assignment.id}:{now.date().isoformat()}",
        )
        if result is not None:
            count += 1
    return count
