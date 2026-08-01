"""Feedback entry CRUD, lifecycle transitions, ratings, and tagging —
GROWTH_AND_INTELLIGENCE.md section 11.2-11.4."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    Complaint,
    FeedbackEntry,
    FeedbackRating,
    FeedbackStatusHistory,
    FeedbackTag,
    StaffUser,
)
from app.feedback.errors import (
    AlreadyConvertedError,
    InvalidStatusTransitionError,
    TransitionNotPermittedError,
)
from app.feedback.schemas import (
    ConvertToComplaintIn,
    FeedbackCreateIn,
    FeedbackStatus,
    FeedbackUpdateIn,
)
from app.permissions.service import has_permission

# section 11.4's lifecycle. "closed" and the terminal side of "spam" have
# no outbound transitions; only `spam` may still be archived via `closed`.
_FEEDBACK_TRANSITIONS: dict[str, set[str]] = {
    "new": {"acknowledged", "spam"},
    "acknowledged": {"under_review", "action_required", "resolved", "spam"},
    "under_review": {"action_required", "resolved"},
    "action_required": {"resolved"},
    "resolved": {"closed"},
    "closed": set(),
    "spam": {"closed"},
}

# `resolved`/`closed` need the base `feedback.resolve` grant beyond
# `feedback.update` — same router-independent gating shape
# `app.complaints.service.GATED_TRANSITIONS` uses.
GATED_TRANSITIONS: dict[str, str] = {
    "resolved": "feedback.resolve",
    "closed": "feedback.resolve",
}


def generate_feedback_number() -> str:
    return f"FB-{uuid.uuid4().hex[:8].upper()}"


async def get_feedback(session: AsyncSession, feedback_id: uuid.UUID) -> FeedbackEntry | None:
    return await session.get(FeedbackEntry, feedback_id)


async def list_feedback(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    source: str | None = None,
    sentiment: str | None = None,
    customer_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    reservation_id: uuid.UUID | None = None,
) -> tuple[list[FeedbackEntry], int]:
    query = select(FeedbackEntry)
    if status:
        query = query.where(FeedbackEntry.status == status)
    if source:
        query = query.where(FeedbackEntry.source == source)
    if sentiment:
        query = query.where(FeedbackEntry.sentiment == sentiment)
    if customer_id:
        query = query.where(FeedbackEntry.customer_id == customer_id)
    if order_id:
        query = query.where(FeedbackEntry.order_id == order_id)
    if reservation_id:
        query = query.where(FeedbackEntry.reservation_id == reservation_id)

    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    query = (
        query.order_by(FeedbackEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list((await session.scalars(query)).all())
    return rows, total or 0


async def create_feedback(
    session: AsyncSession, *, actor: StaffUser | None, payload: FeedbackCreateIn
) -> FeedbackEntry:
    feedback = FeedbackEntry(
        feedback_number=generate_feedback_number(),
        customer_id=payload.customer_id,
        guest_name=payload.guest_name,
        guest_contact=payload.guest_contact,
        source=payload.source,
        order_id=payload.order_id,
        reservation_id=payload.reservation_id,
        campaign_id=payload.campaign_id,
        comment=payload.comment,
        sentiment=payload.sentiment,
        consent_for_follow_up=payload.consent_for_follow_up,
        created_by=actor.id if actor else None,
        updated_by=actor.id if actor else None,
    )
    session.add(feedback)
    await session.flush()

    for rating in payload.ratings:
        session.add(
            FeedbackRating(
                feedback_id=feedback.id, dimension=rating.dimension, rating=rating.rating
            )
        )
    session.add(
        FeedbackStatusHistory(
            feedback_id=feedback.id,
            from_status=None,
            to_status="new",
            actor_id=actor.id if actor else None,
        )
    )
    await session.flush()

    if actor is not None:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="feedback.created",
            target_type="feedback_entry",
            target_id=feedback.id,
            safe_metadata={"source": payload.source},
        )
    return feedback


async def update_feedback(
    session: AsyncSession, *, actor: StaffUser, feedback: FeedbackEntry, payload: FeedbackUpdateIn
) -> FeedbackEntry:
    if payload.assigned_staff_id is not None:
        feedback.assigned_staff_id = payload.assigned_staff_id
    if payload.priority is not None:
        feedback.priority = payload.priority
    if payload.sentiment is not None:
        feedback.sentiment = payload.sentiment
    if payload.comment is not None:
        feedback.comment = payload.comment
    feedback.updated_by = actor.id
    await session.flush()
    return feedback


async def transition_feedback(
    session: AsyncSession,
    *,
    actor: StaffUser,
    feedback: FeedbackEntry,
    target_status: FeedbackStatus,
    reason: str | None = None,
) -> FeedbackEntry:
    allowed = _FEEDBACK_TRANSITIONS.get(feedback.status, set())
    if target_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition feedback from {feedback.status!r} to {target_status!r}."
        )
    required_permission = GATED_TRANSITIONS.get(target_status)
    if required_permission is not None and not await has_permission(
        session, actor.id, required_permission
    ):
        raise TransitionNotPermittedError(
            f"You do not have permission to move feedback to {target_status!r}."
        )

    now = datetime.now(UTC)
    from_status = feedback.status
    feedback.status = target_status
    feedback.updated_by = actor.id
    if target_status == "acknowledged" and feedback.acknowledged_at is None:
        feedback.acknowledged_at = now
    if target_status == "resolved":
        feedback.resolved_at = now
    if target_status == "closed":
        feedback.closed_at = now

    session.add(
        FeedbackStatusHistory(
            feedback_id=feedback.id,
            from_status=from_status,
            to_status=target_status,
            actor_id=actor.id,
            reason=reason,
        )
    )
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="feedback.transitioned",
        target_type="feedback_entry",
        target_id=feedback.id,
        safe_metadata={"from_status": from_status, "to_status": target_status},
    )
    return feedback


async def convert_to_complaint(
    session: AsyncSession,
    *,
    actor: StaffUser,
    feedback: FeedbackEntry,
    payload: ConvertToComplaintIn,
) -> Complaint:
    """Explicit, staff-driven conversion — CLAUDE.md's own rule that "not
    every negative feedback item automatically becomes a complaint;
    complaint conversion must be explicit or rule-driven with full
    auditability." The actual `Complaint` row is created by
    `app.complaints.service.create_complaint` (source_type="feedback"); this
    function only guards against double-conversion and records the
    backlink."""
    if feedback.converted_to_complaint_id is not None:
        raise AlreadyConvertedError("This feedback entry has already been converted.")

    from app.complaints.schemas import ComplaintCreateIn
    from app.complaints.service import create_complaint

    if feedback.customer_id is None:
        raise AlreadyConvertedError(
            "Feedback without a linked customer cannot be converted to a complaint."
        )

    complaint = await create_complaint(
        session,
        actor=actor,
        payload=ComplaintCreateIn(
            customer_id=feedback.customer_id,
            source_type="feedback",
            feedback_id=feedback.id,
            order_id=feedback.order_id,
            reservation_id=feedback.reservation_id,
            category=payload.category,  # type: ignore[arg-type]
            severity=payload.severity,  # type: ignore[arg-type]
            title=payload.title,
            description=payload.description or (feedback.comment or payload.title),
        ),
    )
    feedback.converted_to_complaint_id = complaint.id
    feedback.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="feedback.converted_to_complaint",
        target_type="feedback_entry",
        target_id=feedback.id,
        safe_metadata={"complaint_id": str(complaint.id)},
    )
    return complaint


async def assign_tags(
    session: AsyncSession, *, actor: StaffUser, feedback: FeedbackEntry, tag_ids: list[uuid.UUID]
) -> None:
    existing = await session.scalars(
        select(FeedbackTag.tag_id).where(FeedbackTag.feedback_id == feedback.id)
    )
    existing_ids = set(existing.all())
    for tag_id in tag_ids:
        if tag_id not in existing_ids:
            session.add(FeedbackTag(feedback_id=feedback.id, tag_id=tag_id, assigned_by=actor.id))
    await session.flush()


async def list_ratings(session: AsyncSession, feedback_id: uuid.UUID) -> list[FeedbackRating]:
    result = await session.scalars(
        select(FeedbackRating).where(FeedbackRating.feedback_id == feedback_id)
    )
    return list(result.all())


async def list_status_history(
    session: AsyncSession, feedback_id: uuid.UUID
) -> list[FeedbackStatusHistory]:
    result = await session.scalars(
        select(FeedbackStatusHistory)
        .where(FeedbackStatusHistory.feedback_id == feedback_id)
        .order_by(FeedbackStatusHistory.created_at.asc())
    )
    return list(result.all())


async def customer_feedback_history(
    session: AsyncSession, *, customer_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[FeedbackEntry], int]:
    return await list_feedback(session, page=page, page_size=page_size, customer_id=customer_id)
