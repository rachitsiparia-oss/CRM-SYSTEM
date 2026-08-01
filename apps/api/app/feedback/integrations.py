"""Order/reservation -> review-request integration — wires Phase 13's
review-request outreach into the existing Phase 7/Phase 9 lifecycles
*around* their unmodified state machines, the same additive-integration
model `app.inventory.order_integration` (Phase 8) and
`app.orders.commercial_growth_integration` (Phase 12) already established.

Called from `app.orders.router.transition_order` and
`app.reservations.router` after the underlying transition succeeds —
INTEGRATIONS_AUTOMATIONS_REALTIME.md section 14.1/14.2: "Completed
eligible order schedules a feedback request" / "Completed visit may
schedule feedback request."
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Customer, Order, Reservation, StaffUser
from app.feedback import review_requests
from app.feedback.errors import DuplicateReviewRequestError, FeedbackError
from app.feedback.schemas import ReviewRequestChannel, ReviewRequestCreateIn


def _pick_channel(customer: Customer) -> ReviewRequestChannel | None:
    """Prefers WhatsApp (highest open-rate channel already established by
    Phase 10's own provider priority), falling back to email; a customer
    with neither on file simply has no eligible channel."""
    if customer.primary_phone_e164:
        return "whatsapp"
    if customer.primary_email:
        return "email"
    return None


async def schedule_order_review_request(
    session: AsyncSession, *, actor: StaffUser, order: Order, new_status: str
) -> None:
    if new_status != "completed" or order.customer_id is None:
        return

    customer = await session.get(Customer, order.customer_id)
    if customer is None:
        return
    channel = _pick_channel(customer)
    if channel is None:
        return

    try:
        await review_requests.create_review_request(
            session,
            actor=actor,
            payload=ReviewRequestCreateIn(
                customer_id=customer.id, source_type="order", order_id=order.id, channel=channel
            ),
        )
    except DuplicateReviewRequestError:
        return  # A retried transition must not create a second request.
    except FeedbackError:
        return  # Any other domain-level rejection is not this hook's business to raise.


async def schedule_reservation_review_request(
    session: AsyncSession, *, actor: StaffUser, reservation: Reservation, new_status: str
) -> None:
    if new_status != "completed" or reservation.customer_id is None:
        return

    customer = await session.get(Customer, reservation.customer_id)
    if customer is None:
        return
    channel = _pick_channel(customer)
    if channel is None:
        return

    try:
        await review_requests.create_review_request(
            session,
            actor=actor,
            payload=ReviewRequestCreateIn(
                customer_id=customer.id,
                source_type="reservation",
                reservation_id=reservation.id,
                channel=channel,
            ),
        )
    except DuplicateReviewRequestError:
        return
    except FeedbackError:
        return
