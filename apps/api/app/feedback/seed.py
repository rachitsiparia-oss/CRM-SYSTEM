"""Idempotent development seed data for feedback and review requests —
this phase's own instruction: "linked to existing canonical customers,
orders, reservations, and staff... no fake auth users."

Reuses `app.feedback.service`/`app.feedback.review_requests` directly
(never constructs rows by hand) — the same precedent `app.orders.seed`/
`app.offers.seed` set, so seed data exercises the exact same validation,
eligibility, and auto-escalation logic real API calls do. Each block
queries for an existing row on a natural key before creating, so reruns
never duplicate.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.consent import record_consent
from app.db.models import CommunicationPreference, Customer, FeedbackEntry, Order, StaffUser
from app.feedback import review_requests, service
from app.feedback.errors import DuplicateReviewRequestError
from app.feedback.schemas import (
    ConvertToComplaintIn,
    FeedbackCreateIn,
    RatingIn,
    ReviewRequestCompleteIn,
    ReviewRequestCreateIn,
)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def _customer_id(session: AsyncSession, email: str) -> uuid.UUID | None:
    result: uuid.UUID | None = await session.scalar(
        select(Customer.id).where(Customer.primary_email == email)
    )
    return result


async def _latest_order_id(session: AsyncSession, customer_id: uuid.UUID) -> uuid.UUID | None:
    result: uuid.UUID | None = await session.scalar(
        select(Order.id)
        .where(Order.customer_id == customer_id, Order.status == "completed")
        .order_by(Order.created_at.desc())
        .limit(1)
    )
    return result


async def _seed_order_review_request(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer_id: uuid.UUID,
    order_id: uuid.UUID,
    overall: int,
) -> None:
    try:
        review_request = await review_requests.create_review_request(
            session,
            actor=actor,
            payload=ReviewRequestCreateIn(
                customer_id=customer_id,
                source_type="order",
                order_id=order_id,
                channel="whatsapp",
            ),
        )
    except DuplicateReviewRequestError:
        return

    if review_request.status != "eligible":
        return
    review_request = await review_requests.mark_scheduled(
        session, review_request=review_request, scheduled_at=review_request.created_at
    )
    review_request = await review_requests.mark_sent(session, review_request=review_request)
    review_request = await review_requests.mark_delivered(session, review_request=review_request)
    review_request = await review_requests.mark_opened(session, review_request=review_request)
    await review_requests.complete_review_request(
        session,
        actor=actor,
        review_request=review_request,
        payload=ReviewRequestCompleteIn(
            comment=(
                "Food arrived hot and the packaging held up well."
                if overall >= 4
                else "Order arrived very late and two items were missing."
            ),
            sentiment="positive" if overall >= 4 else "negative",
            ratings=[
                RatingIn(dimension="overall", rating=overall),
                RatingIn(dimension="food_quality", rating=min(5, overall + 1)),
            ],
        ),
    )


async def seed_feedback(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    ananya_id = await _customer_id(session, "ananya.rao@example.test")
    rahul_id = await _customer_id(session, "rahul.mehta@example.test")
    karthik_id = await _customer_id(session, "karthik.iyer@example.test")

    if ananya_id is not None:
        # Review requests are promotional sends — grant WhatsApp opt-in first
        # (mirrors a real customer opting in at checkout) so the seeded
        # request clears `evaluate_send_eligibility` instead of landing
        # `suppressed`/`no_consent`. `record_consent` always appends a new
        # append-only log row, so this is gated on the *current* preference
        # state to keep reruns idempotent.
        preference = await session.scalar(
            select(CommunicationPreference).where(CommunicationPreference.customer_id == ananya_id)
        )
        if preference is None or not preference.allow_promotional_whatsapp:
            await record_consent(
                session,
                customer_id=ananya_id,
                consent_type="promotional_whatsapp",
                consent_given=True,
                source="staff_entry",
                actor=actor,
            )
        ananya_order_id = await _latest_order_id(session, ananya_id)
        if ananya_order_id is not None:
            await _seed_order_review_request(
                session, actor=actor, customer_id=ananya_id, order_id=ananya_order_id, overall=5
            )

    if rahul_id is not None:
        rahul_order_id = await _latest_order_id(session, rahul_id)
        if rahul_order_id is not None:
            # Overall <= 2 exercises `review_requests.complete_review_request`'s
            # auto-acknowledge/action-required escalation path.
            await _seed_order_review_request(
                session, actor=actor, customer_id=rahul_id, order_id=rahul_order_id, overall=2
            )

    if karthik_id is not None:
        existing = await session.scalar(
            select(FeedbackEntry).where(
                FeedbackEntry.customer_id == karthik_id, FeedbackEntry.source == "whatsapp"
            )
        )
        if existing is None:
            feedback = await service.create_feedback(
                session,
                actor=actor,
                payload=FeedbackCreateIn(
                    customer_id=karthik_id,
                    source="whatsapp",
                    comment="The delivery rider was rude and the order was over an hour late.",
                    sentiment="negative",
                    consent_for_follow_up=True,
                    ratings=[RatingIn(dimension="overall", rating=1)],
                ),
            )
            await service.convert_to_complaint(
                session,
                actor=actor,
                feedback=feedback,
                payload=ConvertToComplaintIn(
                    category="delivery",
                    severity="medium",
                    title="Late delivery with unprofessional rider conduct",
                    description=feedback.comment,
                ),
            )
