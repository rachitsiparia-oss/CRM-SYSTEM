"""Order-to-commercial-growth integration — wires Phase 12's Loyalty,
Offers, Achievements, and Referrals domains into the order lifecycle
*around* the unmodified Phase 7 state machine, the exact "integrate
safely without weakening its validation" model
`app.inventory.order_integration` already established for stock effects.

Called from the router *after* `transition_order_with_inventory` so
`order.status` already reflects the transition when these hooks run.

**Discovered dependency, fixed here rather than deferred**: `Customer`'s
own docstring says its order-derived roll-up columns
(`completed_order_count`, `lifetime_value_minor`,
`average_order_value_minor`, `first_order_at`, `last_order_at`) stay at
zero/NULL "until Phase 7 (Orders) actually writes them" — but no Phase 7
code path ever did. Every Phase 12 rule evaluation
(`app.commercial_rules.facts.resolve_customer_facts`) reads those exact
columns, so leaving them unwritten would make segment/offer/achievement
conditions silently non-functional against real order data. This module
writes them on `completed`, the same place Phase 7's own docstring says
they belong — it does not change Phase 7's state machine or any of its
files.

**Payment gating**: loyalty earning and referral qualification require
`payment_status == 'paid'`, matching GROWTH_AND_INTELLIGENCE.md section
7.2's "first completed, paid, direct order." Achievement evaluation and
the customer roll-up update run on `completed` regardless of
payment_status, since an unpaid completed order is still a real
fulfilled order for count/spend purposes is a judgment call this module
does not make silently — see the inline note on `_update_customer_rollup`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.achievements import awards as achievement_awards
from app.achievements import service as achievement_service
from app.achievements.errors import AchievementError
from app.audit.service import record_audit_event
from app.db.models import (
    AuditEvent,
    Customer,
    OfferRedemption,
    Order,
    ReferralProgram,
    ReferralRelationship,
    StaffUser,
)
from app.loyalty.errors import DuplicateIdempotencyKeyError
from app.offers import redemptions as offer_redemptions
from app.offers.errors import OfferError
from app.referrals import relationships as referral_relationships
from app.referrals.errors import ReferralError

_ROLLUP_ACTION_CODE = "commercial_growth.customer_rollup_updated"


async def _update_customer_rollup(
    session: AsyncSession, *, actor: StaffUser, customer: Customer, order: Order
) -> None:
    """Runs once per completed order, regardless of payment_status — an
    order that reached 'completed' was fulfilled; refund/payment failure
    after the fact is tracked separately via `payment_status` and does not
    retroactively un-fulfil it. Money-in-transit accounting stays Phase 7's
    concern; this only maintains the count/spend projection Phase 12 reads.

    Guarded by a dedicated audit-event marker (`_ROLLUP_ACTION_CODE`
    against `target_type="order"`) so a retried/duplicate `completed`
    transition for the same order never double-counts — the same
    idempotency guarantee `_earn_loyalty_points` gets for free from its
    ledger idempotency key, applied here since this function has no
    ledger of its own to key against.
    """
    already_applied = await session.scalar(
        select(AuditEvent.id).where(
            AuditEvent.action_code == _ROLLUP_ACTION_CODE,
            AuditEvent.target_type == "order",
            AuditEvent.target_id == order.id,
        )
    )
    if already_applied is not None:
        return

    now = datetime.now(UTC)
    customer.completed_order_count += 1
    customer.lifetime_value_minor += order.grand_total_minor
    customer.average_order_value_minor = (
        customer.lifetime_value_minor // customer.completed_order_count
    )
    if customer.first_order_at is None:
        customer.first_order_at = now
    customer.last_order_at = now
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code=_ROLLUP_ACTION_CODE,
        target_type="order",
        target_id=order.id,
        safe_metadata={"customer_id": str(customer.id)},
    )


async def _earn_loyalty_points(
    session: AsyncSession, *, actor: StaffUser, customer: Customer, order: Order
) -> None:
    from app.loyalty import accounts as loyalty_accounts
    from app.loyalty import ledger as loyalty_ledger
    from app.loyalty import programs as loyalty_programs
    from app.loyalty.schemas import EnrollIn

    program = await loyalty_programs.get_default_program(session)
    if program is None:
        return

    points = (
        order.grand_total_minor // program.currency_unit_minor
    ) * program.points_per_currency_unit
    if points <= 0:
        return

    account = await loyalty_accounts.enroll(
        session, actor=actor, payload=EnrollIn(customer_id=customer.id, program_id=program.id)
    )
    try:
        await loyalty_ledger.post_entry(
            session,
            account_id=account.id,
            entry_type="earn_order",
            points=points,
            idempotency_key=f"order-earn:{order.id}",
            actor_id=actor.id,
            source_type="order",
            source_id=order.id,
            description=f"Points earned on order {order.order_number}",
        )
    except DuplicateIdempotencyKeyError:
        return  # This order already earned points — a retried transition, not an error.
    await loyalty_accounts.evaluate_and_apply_tier(session, account=account)


async def _evaluate_achievements(
    session: AsyncSession, *, actor: StaffUser, customer: Customer, order: Order
) -> None:
    achievements, _ = await achievement_service.list_achievements(
        session, page=1, page_size=100, is_active=True
    )
    for achievement in achievements:
        try:
            await achievement_awards.evaluate_and_award(
                session,
                actor=actor,
                achievement=achievement,
                customer_id=customer.id,
                source_event_type="order_completed",
                source_event_key=f"order:{order.id}:{achievement.id}",
            )
        except AchievementError:
            continue  # Not eligible / already awarded / on cooldown — expected, not a failure.


async def _qualify_referral(
    session: AsyncSession, *, actor: StaffUser, customer: Customer, order: Order
) -> None:
    relationship = await session.scalar(
        select(ReferralRelationship).where(
            ReferralRelationship.referred_customer_id == customer.id,
            ReferralRelationship.status.in_(["invited", "attributed"]),
            ReferralRelationship.qualifying_order_id.is_(None),
        )
    )
    if relationship is None:
        return
    if customer.completed_order_count != 1:
        return  # Only the referred customer's first completed order qualifies.

    program = await session.get(ReferralProgram, relationship.program_id)
    if program is None or program.status != "active":
        return
    minimum = program.qualifying_order_minimum_minor or 0
    if order.grand_total_minor < minimum:
        return

    try:
        await referral_relationships.qualify(
            session, actor=actor, relationship=relationship, qualifying_order_id=order.id
        )
    except ReferralError:
        return


async def _confirm_offer_redemptions(
    session: AsyncSession, *, actor: StaffUser, order: Order
) -> None:
    rows = await session.scalars(
        select(OfferRedemption).where(
            OfferRedemption.order_id == order.id, OfferRedemption.status == "reserved"
        )
    )
    for redemption in rows:
        try:
            await offer_redemptions.confirm(
                session, redemption=redemption, order_id=order.id, actor=actor
            )
        except OfferError:
            continue


async def _release_offer_redemptions(
    session: AsyncSession, *, actor: StaffUser, order: Order
) -> None:
    reserved = await session.scalars(
        select(OfferRedemption).where(
            OfferRedemption.order_id == order.id, OfferRedemption.status == "reserved"
        )
    )
    for redemption in reserved:
        try:
            await offer_redemptions.reject(
                session, redemption=redemption, reason="Order cancelled", actor=actor
            )
        except OfferError:
            continue

    confirmed = await session.scalars(
        select(OfferRedemption).where(
            OfferRedemption.order_id == order.id, OfferRedemption.status == "confirmed"
        )
    )
    for redemption in confirmed:
        try:
            await offer_redemptions.reverse(
                session, redemption=redemption, reason="Order cancelled", actor=actor
            )
        except OfferError:
            continue


async def apply_commercial_growth_effects(
    session: AsyncSession, *, actor: StaffUser, order: Order, new_status: str
) -> None:
    if new_status == "confirmed":
        await _confirm_offer_redemptions(session, actor=actor, order=order)
        return

    if new_status == "cancelled":
        await _release_offer_redemptions(session, actor=actor, order=order)
        return

    if new_status != "completed" or order.customer_id is None:
        return

    customer = await session.get(Customer, order.customer_id)
    if customer is None:
        return

    await _update_customer_rollup(session, actor=actor, customer=customer, order=order)
    await _evaluate_achievements(session, actor=actor, customer=customer, order=order)

    if order.payment_status == "paid":
        await _earn_loyalty_points(session, actor=actor, customer=customer, order=order)
        await _qualify_referral(session, actor=actor, customer=customer, order=order)
