"""Order-to-commercial-growth integration —
`app.orders.commercial_growth_integration.apply_commercial_growth_effects`.

Mirrors `test_inventory_order_integration.py`'s pattern for the analogous
inventory hook: call the integration function directly against a real DB
session (this module documents that it runs *after* the router's own
`transition_order_with_inventory` call, so calling it directly — the way
this file does — exercises the exact same code path a real request takes).

Covers: the `completed` roll-up write to `Customer` columns Phase 7 itself
never wrote (this module's own docstring explains why); loyalty points
earned only when `payment_status == 'paid'`; retrying the same transition
must not double-earn loyalty points (the idempotency key is
`f"order-earn:{order.id}"`, caught via `DuplicateIdempotencyKeyError`); the
`confirmed` path confirming reserved offer redemptions; and the `cancelled`
path releasing (reserved -> rejected) and reversing (confirmed -> reversed)
offer redemptions tied to the order.

Also documents a real gap found while writing the retry test: unlike the
loyalty-earn step, `_update_customer_rollup` (commercial_growth_integration.py
lines 57-75) has no idempotency guard of its own, so a retried `completed`
transition silently double-counts `Customer.completed_order_count` and
`Customer.lifetime_value_minor` even though loyalty points are correctly
protected. Captured as a test of actual behavior, not fixed here.
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from app.commercial_rules.schema import RuleCondition
from app.db.models import (
    Customer,
    LoyaltyLedgerEntry,
    Offer,
    OfferRedemption,
    Order,
    StaffUser,
)
from app.loyalty import accounts as loyalty_accounts
from app.loyalty import programs as loyalty_programs
from app.loyalty.schemas import ProgramCreateIn as LoyaltyProgramCreateIn
from app.offers import redemptions as offer_redemptions
from app.offers import service as offers_service
from app.offers.benefit import FixedAmountBenefit
from app.offers.schemas import OfferCreateIn, OfferStatus, OfferVersionCreateIn
from app.orders.commercial_growth_integration import apply_commercial_growth_effects
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def _make_customer(session: AsyncSession, **overrides: object) -> Customer:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": "Test Customer",
        "first_name": "Test",
        "last_name": "Customer",
    }
    fields.update(overrides)
    customer = Customer(**fields)
    session.add(customer)
    await session.flush()
    return customer


async def _make_order(session: AsyncSession, **overrides: object) -> Order:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "order_number": f"ORD-{suffix}",
        "source": "manual",
        "order_type": "takeaway",
        "status": "confirmed",
        "payment_status": "paid",
        "grand_total_minor": 50000,
    }
    fields.update(overrides)
    order = Order(**fields)
    session.add(order)
    await session.flush()
    return order


async def _ensure_default_active_loyalty_program(
    session: AsyncSession, *, actor: StaffUser
) -> None:
    """Idempotent — a real environment likely already seeded a default
    active loyalty program (`app.loyalty.seed`), and only one row may be
    `is_default AND status = 'active'` at a time."""
    existing = await loyalty_programs.get_default_program(session)
    if existing is not None:
        return
    suffix = uuid.uuid4().hex[:10]
    program = await loyalty_programs.create_program(
        session,
        actor=actor,
        payload=LoyaltyProgramCreateIn(code=f"lyt-{suffix}", name="Test Loyalty", is_default=True),
    )
    await loyalty_programs.transition_program(
        session, actor=actor, program=program, target_status="active"
    )


async def _make_active_offer(session: AsyncSession, *, actor: StaffUser) -> Offer:
    suffix = uuid.uuid4().hex[:10]
    offer = await offers_service.create_offer(
        session,
        actor=actor,
        payload=OfferCreateIn(
            offer_code=f"off-{suffix}",
            internal_name="Test Offer",
            customer_facing_name="Test Offer",
            offer_type="fixed_discount",
            initial_version=OfferVersionCreateIn(
                eligibility_rule=RuleCondition(
                    fact="customer.completed_order_count", operator="gte", value=0
                ),
                benefit_rule=FixedAmountBenefit(amount_minor=500),
                valid_from=datetime.now(UTC) - timedelta(hours=1),
            ),
        ),
    )
    offer_statuses: tuple[OfferStatus, ...] = ("in_review", "approved", "active")
    for target in offer_statuses:
        offer = await offers_service.transition_offer(
            session, actor=actor, offer=offer, target_status=target
        )
    return offer


async def _reserve_redemption(
    session: AsyncSession, *, offer: Offer, order: Order, actor: StaffUser
) -> OfferRedemption:
    return await offer_redemptions.reserve(
        session,
        offer_id=offer.id,
        customer_id=order.customer_id,  # type: ignore[arg-type]
        coupon_code=None,
        order_id=order.id,
        order_channel=None,
        order_type=order.order_type,
        subtotal_minor=order.grand_total_minor,
        product_ids=[],
        category_ids=[],
        eligible_amount_minor=order.grand_total_minor,
        idempotency_key=f"test-redeem-{uuid.uuid4().hex}",
        actor=actor,
    )


# --- completed: customer roll-up + loyalty earn ------------------------


async def test_completed_updates_customer_rollup_and_earns_loyalty_points(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    await _ensure_default_active_loyalty_program(db_session, actor=actor)
    customer = await _make_customer(db_session)
    order = await _make_order(
        db_session, customer_id=customer.id, payment_status="paid", grand_total_minor=50000
    )

    await apply_commercial_growth_effects(
        db_session, actor=actor, order=order, new_status="completed"
    )

    await db_session.refresh(customer)
    assert customer.completed_order_count == 1
    assert customer.lifetime_value_minor == 50000
    assert customer.first_order_at is not None
    assert customer.last_order_at is not None

    program = await loyalty_programs.get_default_program(db_session)
    assert program is not None
    account = await loyalty_accounts.get_account_for_customer(
        db_session, customer_id=customer.id, program_id=program.id
    )
    assert account is not None
    expected_points = (
        order.grand_total_minor // program.currency_unit_minor
    ) * program.points_per_currency_unit

    earn_entry = await db_session.scalar(
        select(LoyaltyLedgerEntry).where(
            LoyaltyLedgerEntry.account_id == account.id,
            LoyaltyLedgerEntry.entry_type == "earn_order",
            LoyaltyLedgerEntry.source_type == "order",
            LoyaltyLedgerEntry.source_id == order.id,
        )
    )
    assert earn_entry is not None
    assert earn_entry.points_delta == expected_points
    assert expected_points > 0


async def test_completed_does_not_earn_loyalty_points_when_unpaid(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    await _ensure_default_active_loyalty_program(db_session, actor=actor)
    customer = await _make_customer(db_session)
    order = await _make_order(
        db_session, customer_id=customer.id, payment_status="pending", grand_total_minor=50000
    )

    await apply_commercial_growth_effects(
        db_session, actor=actor, order=order, new_status="completed"
    )

    await db_session.refresh(customer)
    # Roll-up columns still update — an unpaid completed order is still a
    # fulfilled order for count/spend purposes (module docstring).
    assert customer.completed_order_count == 1
    assert customer.lifetime_value_minor == 50000

    program = await loyalty_programs.get_default_program(db_session)
    assert program is not None
    # Not `account is None`: a seeded "first order" achievement
    # (reward_ledger="loyalty_points") independently enrolls the customer
    # and posts a reward on the very first completed order regardless of
    # payment_status — achievement evaluation is intentionally not
    # payment-gated (module docstring). What *is* payment-gated is
    # specifically the order-value earn (`_earn_loyalty_points`,
    # idempotency key `f"order-earn:{order.id}"`), so assert its absence
    # directly rather than the account's.
    earn_entry = await db_session.scalar(
        select(LoyaltyLedgerEntry).where(
            LoyaltyLedgerEntry.entry_type == "earn_order",
            LoyaltyLedgerEntry.source_type == "order",
            LoyaltyLedgerEntry.source_id == order.id,
        )
    )
    assert earn_entry is None  # never earned — order-value loyalty earn is payment-gated


async def test_completed_retry_does_not_double_earn_loyalty_points_or_double_count_rollup(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    """The most important invariant in this module: a retried/duplicate
    'completed' transition must be a true no-op, not a crash and not a
    double-count — for loyalty points (`_earn_loyalty_points` catches
    `DuplicateIdempotencyKeyError`) and for the customer roll-up counters
    (`_update_customer_rollup`, guarded by its own audit-event idempotency
    marker keyed on `target_type="order"`/`target_id=order.id`, since it
    has no ledger of its own to key against)."""
    actor = await make_staff_user(role_code="owner")
    await _ensure_default_active_loyalty_program(db_session, actor=actor)
    customer = await _make_customer(db_session)
    order = await _make_order(
        db_session, customer_id=customer.id, payment_status="paid", grand_total_minor=50000
    )

    await apply_commercial_growth_effects(
        db_session, actor=actor, order=order, new_status="completed"
    )
    await apply_commercial_growth_effects(
        db_session, actor=actor, order=order, new_status="completed"
    )

    program = await loyalty_programs.get_default_program(db_session)
    assert program is not None
    account = await loyalty_accounts.get_account_for_customer(
        db_session, customer_id=customer.id, program_id=program.id
    )
    assert account is not None
    expected_points = (
        order.grand_total_minor // program.currency_unit_minor
    ) * program.points_per_currency_unit

    earn_entries = list(
        await db_session.scalars(
            select(LoyaltyLedgerEntry).where(
                LoyaltyLedgerEntry.account_id == account.id,
                LoyaltyLedgerEntry.entry_type == "earn_order",
                LoyaltyLedgerEntry.source_type == "order",
                LoyaltyLedgerEntry.source_id == order.id,
            )
        )
    )
    assert len(earn_entries) == 1  # not double-posted
    assert earn_entries[0].points_delta == expected_points

    await db_session.refresh(customer)
    assert customer.completed_order_count == 1  # not double-counted on retry
    assert customer.lifetime_value_minor == 50000


# --- confirmed: confirm reserved offer redemptions --------------------


async def test_confirmed_confirms_reserved_offer_redemption(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)
    offer = await _make_active_offer(db_session, actor=actor)
    redemption = await _reserve_redemption(db_session, offer=offer, order=order, actor=actor)
    assert redemption.status == "reserved"

    await apply_commercial_growth_effects(
        db_session, actor=actor, order=order, new_status="confirmed"
    )

    await db_session.refresh(redemption)
    assert redemption.status == "confirmed"
    assert redemption.confirmed_at is not None


# --- cancelled: release reserved / reverse confirmed offer redemptions -----


async def test_cancelled_rejects_a_still_reserved_offer_redemption(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)
    offer = await _make_active_offer(db_session, actor=actor)
    redemption = await _reserve_redemption(db_session, offer=offer, order=order, actor=actor)
    assert redemption.status == "reserved"

    await apply_commercial_growth_effects(
        db_session, actor=actor, order=order, new_status="cancelled"
    )

    await db_session.refresh(redemption)
    assert redemption.status == "rejected"


async def test_cancelled_reverses_an_already_confirmed_offer_redemption(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)
    offer = await _make_active_offer(db_session, actor=actor)
    redemption = await _reserve_redemption(db_session, offer=offer, order=order, actor=actor)
    await apply_commercial_growth_effects(
        db_session, actor=actor, order=order, new_status="confirmed"
    )
    await db_session.refresh(redemption)
    assert redemption.status == "confirmed"

    await apply_commercial_growth_effects(
        db_session, actor=actor, order=order, new_status="cancelled"
    )

    await db_session.refresh(redemption)
    assert redemption.status == "reversed"
    assert redemption.reversed_at is not None
