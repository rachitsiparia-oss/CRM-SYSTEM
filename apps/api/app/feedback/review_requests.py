"""Review-request lifecycle — GROWTH_AND_INTELLIGENCE.md section 11.6.

The outreach half of feedback: asking a customer to rate a completed,
eligible order or visit. What they submit becomes a `FeedbackEntry`
(`complete_review_request`). Actual outbound delivery through a live
WhatsApp/email/SMS provider is Phase 10's channel infrastructure, invoked
here through the same `evaluate_send_eligibility` consent/suppression gate
every other outbound communication in this codebase goes through — no
second consent system. Live recurring dispatch through `apps/worker` is
Phase 15's scope; `process_pending_review_requests` below is the
deterministic, idempotent, directly-callable unit Phase 15 will schedule.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.consent import evaluate_send_eligibility
from app.db.models import CommunicationChannel, Complaint, Customer, ReviewRequest, StaffUser
from app.feedback import service as feedback_service
from app.feedback.errors import (
    DuplicateReviewRequestError,
    InvalidReviewRequestTransitionError,
    ReviewRequestNotEligibleError,
)
from app.feedback.schemas import FeedbackCreateIn, ReviewRequestCompleteIn, ReviewRequestCreateIn

# A customer with an unresolved high/critical complaint should not be
# asked to leave a review — GROWTH_AND_INTELLIGENCE.md section 11.6's
# "exclude customers with unresolved severe complaints where appropriate".
_UNRESOLVED_STATUSES = (
    "new",
    "acknowledged",
    "investigating",
    "awaiting_customer",
    "awaiting_internal",
    "resolution_proposed",
    "reopened",
)
_COOLDOWN_DAYS = 14
_CHANNEL_CODE_TO_FIELD = {
    "whatsapp": "primary_phone_e164",
    "sms": "primary_phone_e164",
    "email": "primary_email",
}

_REVIEW_REQUEST_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"eligible", "suppressed", "cancelled"},
    "eligible": {"scheduled", "cancelled"},
    "scheduled": {"sent", "cancelled", "failed"},
    "sent": {"delivered", "failed", "expired"},
    "delivered": {"opened", "expired"},
    "opened": {"completed", "expired"},
    "completed": set(),
    "expired": set(),
    "suppressed": set(),
    "cancelled": set(),
    "failed": set(),
}


def _idempotency_key(source_type: str, source_id: uuid.UUID) -> str:
    return f"{source_type}:{source_id}"


async def get_review_request(
    session: AsyncSession, review_request_id: uuid.UUID
) -> ReviewRequest | None:
    return await session.get(ReviewRequest, review_request_id)


async def list_review_requests(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
) -> tuple[list[ReviewRequest], int]:
    from sqlalchemy import func

    query = select(ReviewRequest)
    if status:
        query = query.where(ReviewRequest.status == status)
    if customer_id:
        query = query.where(ReviewRequest.customer_id == customer_id)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    query = (
        query.order_by(ReviewRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list((await session.scalars(query)).all())
    return rows, total or 0


async def create_review_request(
    session: AsyncSession, *, actor: StaffUser, payload: ReviewRequestCreateIn
) -> ReviewRequest:
    source_id = payload.order_id if payload.source_type == "order" else payload.reservation_id
    assert source_id is not None  # enforced by the schema's own validator
    idempotency_key = _idempotency_key(payload.source_type, source_id)

    existing = await session.scalar(
        select(ReviewRequest).where(ReviewRequest.idempotency_key == idempotency_key)
    )
    if existing is not None:
        raise DuplicateReviewRequestError(
            "A review request already exists for this order or reservation."
        )

    review_request = ReviewRequest(
        customer_id=payload.customer_id,
        source_type=payload.source_type,
        order_id=payload.order_id,
        reservation_id=payload.reservation_id,
        channel=payload.channel,
        idempotency_key=idempotency_key,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(review_request)
    await session.flush()
    await evaluate_eligibility(session, review_request=review_request)
    return review_request


async def evaluate_eligibility(
    session: AsyncSession, *, review_request: ReviewRequest
) -> ReviewRequest:
    """Idempotent — safe to call again on a `draft` request; a no-op on
    anything already past `draft`."""
    if review_request.status != "draft":
        return review_request

    open_complaint = await session.scalar(
        select(Complaint.id).where(
            Complaint.customer_id == review_request.customer_id,
            Complaint.severity.in_(["high", "critical"]),
            Complaint.status.in_(_UNRESOLVED_STATUSES),
        )
    )
    if open_complaint is not None:
        review_request.status = "suppressed"
        review_request.suppression_reason = "unresolved_severe_complaint"
        await session.flush()
        return review_request

    cooldown_cutoff = datetime.now(UTC) - timedelta(days=_COOLDOWN_DAYS)
    recent = await session.scalar(
        select(ReviewRequest.id).where(
            ReviewRequest.customer_id == review_request.customer_id,
            ReviewRequest.id != review_request.id,
            ReviewRequest.created_at >= cooldown_cutoff,
            ReviewRequest.status.not_in(["draft", "cancelled", "failed"]),
        )
    )
    if recent is not None:
        review_request.status = "suppressed"
        review_request.suppression_reason = "cooldown_active"
        await session.flush()
        return review_request

    customer = await session.get(Customer, review_request.customer_id)
    destination_field = _CHANNEL_CODE_TO_FIELD[review_request.channel]
    destination = getattr(customer, destination_field, None) if customer else None
    channel = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.code == review_request.channel)
    )
    if channel is None or destination is None:
        review_request.status = "suppressed"
        review_request.suppression_reason = "no_channel_or_destination"
        await session.flush()
        return review_request

    eligibility = await evaluate_send_eligibility(
        session,
        channel=channel,
        destination_reference=destination,
        customer_id=review_request.customer_id,
        is_transactional=False,
    )
    if not eligibility.allowed:
        review_request.status = "suppressed"
        review_request.suppression_reason = eligibility.reason
    else:
        review_request.status = "eligible"
        review_request.eligibility_reason = "eligible"
    await session.flush()
    return review_request


def _transition(review_request: ReviewRequest, target_status: str) -> None:
    allowed = _REVIEW_REQUEST_TRANSITIONS.get(review_request.status, set())
    if target_status not in allowed:
        raise InvalidReviewRequestTransitionError(
            f"Cannot transition review request from {review_request.status!r} to {target_status!r}."
        )
    review_request.status = target_status


async def mark_scheduled(
    session: AsyncSession, *, review_request: ReviewRequest, scheduled_at: datetime
) -> ReviewRequest:
    _transition(review_request, "scheduled")
    review_request.scheduled_at = scheduled_at
    await session.flush()
    return review_request


async def mark_sent(session: AsyncSession, *, review_request: ReviewRequest) -> ReviewRequest:
    _transition(review_request, "sent")
    review_request.sent_at = datetime.now(UTC)
    await session.flush()
    return review_request


async def mark_delivered(session: AsyncSession, *, review_request: ReviewRequest) -> ReviewRequest:
    _transition(review_request, "delivered")
    review_request.delivered_at = datetime.now(UTC)
    await session.flush()
    return review_request


async def mark_opened(session: AsyncSession, *, review_request: ReviewRequest) -> ReviewRequest:
    _transition(review_request, "opened")
    review_request.opened_at = datetime.now(UTC)
    await session.flush()
    return review_request


async def mark_failed(
    session: AsyncSession, *, review_request: ReviewRequest, reason: str
) -> ReviewRequest:
    _transition(review_request, "failed")
    review_request.failure_reason = reason
    await session.flush()
    return review_request


async def mark_expired(session: AsyncSession, *, review_request: ReviewRequest) -> ReviewRequest:
    _transition(review_request, "expired")
    review_request.expired_at = datetime.now(UTC)
    await session.flush()
    return review_request


async def cancel_review_request(
    session: AsyncSession, *, review_request: ReviewRequest
) -> ReviewRequest:
    _transition(review_request, "cancelled")
    await session.flush()
    return review_request


async def complete_review_request(
    session: AsyncSession,
    *,
    actor: StaffUser | None,
    review_request: ReviewRequest,
    payload: ReviewRequestCompleteIn,
) -> ReviewRequest:
    if review_request.status not in ("sent", "delivered", "opened"):
        raise ReviewRequestNotEligibleError(
            "A review request must have been sent before it can be completed."
        )

    feedback = await feedback_service.create_feedback(
        session,
        actor=actor,
        payload=FeedbackCreateIn(
            customer_id=review_request.customer_id,
            source="post_order" if review_request.source_type == "order" else "post_reservation",
            order_id=review_request.order_id,
            reservation_id=review_request.reservation_id,
            comment=payload.comment,
            sentiment=payload.sentiment,
            consent_for_follow_up=True,
            ratings=payload.ratings,
        ),
    )

    overall = next((r.rating for r in payload.ratings if r.dimension == "overall"), None)
    if overall is not None and overall <= 2 and actor is not None:
        # "Low rating creates action-required status" —
        # INTEGRATIONS_AUTOMATIONS_REALTIME.md section 14.6.
        await feedback_service.transition_feedback(
            session,
            actor=actor,
            feedback=feedback,
            target_status="acknowledged",
            reason="Auto-acknowledged: low rating from review request.",
        )
        await feedback_service.transition_feedback(
            session,
            actor=actor,
            feedback=feedback,
            target_status="action_required",
            reason="Auto-flagged: overall rating <= 2 from a review request.",
        )

    review_request.status = "completed"
    review_request.completed_at = datetime.now(UTC)
    review_request.resulting_feedback_id = feedback.id
    await session.flush()
    return review_request


async def process_pending_review_requests(session: AsyncSession) -> list[ReviewRequest]:
    """Deterministic, idempotent: re-evaluates eligibility for every
    `draft` request and expires anything `sent`/`delivered`/`opened` for
    more than 14 days without completion. Safe to call repeatedly; a
    future Phase 15 schedule is the only thing that would call it
    automatically."""
    processed: list[ReviewRequest] = []

    draft_rows = list(
        (await session.scalars(select(ReviewRequest).where(ReviewRequest.status == "draft"))).all()
    )
    for row in draft_rows:
        await evaluate_eligibility(session, review_request=row)
        processed.append(row)

    expiry_cutoff = datetime.now(UTC) - timedelta(days=14)
    stale_rows = list(
        (
            await session.scalars(
                select(ReviewRequest).where(
                    ReviewRequest.status.in_(["sent", "delivered", "opened"]),
                    ReviewRequest.created_at < expiry_cutoff,
                )
            )
        ).all()
    )
    for row in stale_rows:
        await mark_expired(session, review_request=row)
        processed.append(row)

    return processed
