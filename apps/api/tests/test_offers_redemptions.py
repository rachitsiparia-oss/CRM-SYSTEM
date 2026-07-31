"""Real-DB tests for `app.offers.redemptions` and `app.offers.coupons` — the
reserve -> confirm/reject/reverse lifecycle, capacity accounting
(`Offer.redemption_count`/`Coupon.redemption_count`), idempotency, and
coupon-gated redemption.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.commercial_rules.schema import RuleCondition
from app.db.models import Coupon, Customer, Offer, OfferRedemption, Order, StaffUser
from app.offers import coupons as coupons_service
from app.offers import redemptions, service
from app.offers.benefit import PercentageBenefit
from app.offers.errors import (
    DuplicateIdempotencyKeyError,
    InvalidRedemptionStateError,
    NotEligibleError,
    RedemptionLimitReachedError,
)
from app.offers.schemas import CouponCreateIn, OfferCreateIn, OfferVersionCreateIn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]

# Trivially satisfiable for any customer — the eligibility_rule engine is
# covered separately by test_commercial_rules_evaluator.py; these tests
# focus on the redemption lifecycle around it.
_ALWAYS_TRUE_RULE = RuleCondition(fact="customer.completed_order_count", operator="gte", value=0)


def _customer_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": "Test Customer",
        "first_name": "Test",
        "last_name": "Customer",
    }
    base.update(overrides)
    return base


async def _make_customer(session: AsyncSession, **overrides: object) -> Customer:
    customer = Customer(**_customer_kwargs(**overrides))
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
        "status": "draft",
        "payment_status": "pending",
    }
    fields.update(overrides)
    order = Order(**fields)
    session.add(order)
    await session.flush()
    return order


async def _make_active_offer(
    session: AsyncSession,
    *,
    actor: StaffUser,
    requires_code: bool = False,
    global_usage_limit: int | None = None,
    per_customer_usage_limit: int | None = None,
    percent: Decimal = Decimal("10"),
) -> Offer:
    payload = OfferCreateIn(
        offer_code=f"OFFER-{uuid.uuid4().hex[:10]}",
        internal_name="Test offer",
        customer_facing_name="Test offer",
        offer_type="percentage_discount",
        requires_code=requires_code,
        initial_version=OfferVersionCreateIn(
            eligibility_rule=_ALWAYS_TRUE_RULE,
            benefit_rule=PercentageBenefit(percent=percent),
            global_usage_limit=global_usage_limit,
            per_customer_usage_limit=per_customer_usage_limit,
            valid_from=datetime.now(UTC) - timedelta(days=1),
        ),
    )
    offer = await service.create_offer(session, actor=actor, payload=payload)
    offer = await service.transition_offer(
        session, actor=actor, offer=offer, target_status="in_review"
    )
    offer = await service.transition_offer(
        session, actor=actor, offer=offer, target_status="approved"
    )
    offer = await service.transition_offer(
        session, actor=actor, offer=offer, target_status="active"
    )
    return offer


async def _reserve(
    session: AsyncSession,
    *,
    offer: Offer,
    customer_id: uuid.UUID,
    idempotency_key: str | None = None,
    coupon_code: str | None = None,
    actor: StaffUser | None = None,
) -> OfferRedemption:
    return await redemptions.reserve(
        session,
        offer_id=offer.id,
        customer_id=customer_id,
        coupon_code=coupon_code,
        order_id=None,
        order_channel="dine_in",
        order_type="dine_in",
        subtotal_minor=1000,
        product_ids=[],
        category_ids=[],
        eligible_amount_minor=1000,
        idempotency_key=idempotency_key or f"idem-{uuid.uuid4().hex}",
        actor=actor,
    )


# --- reserve / capacity accounting -----------------------------------------


async def test_reserve_succeeds_and_increments_offer_redemption_count(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor)
    customer = await _make_customer(db_session)

    redemption = await _reserve(db_session, offer=offer, customer_id=customer.id, actor=actor)

    assert redemption.status == "reserved"
    assert redemption.discount_amount_minor == 100  # 10% of 1000
    assert offer.redemption_count == 1


async def test_reserve_duplicate_idempotency_key_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor)
    customer = await _make_customer(db_session)
    key = f"idem-{uuid.uuid4().hex}"

    await _reserve(
        db_session, offer=offer, customer_id=customer.id, idempotency_key=key, actor=actor
    )
    with pytest.raises(DuplicateIdempotencyKeyError):
        await _reserve(
            db_session, offer=offer, customer_id=customer.id, idempotency_key=key, actor=actor
        )
    assert offer.redemption_count == 1  # not double-reserved


async def test_reserve_rejected_when_global_usage_limit_reached(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor, global_usage_limit=1)
    first_customer = await _make_customer(db_session)
    second_customer = await _make_customer(db_session)

    await _reserve(db_session, offer=offer, customer_id=first_customer.id, actor=actor)
    with pytest.raises(RedemptionLimitReachedError):
        await _reserve(db_session, offer=offer, customer_id=second_customer.id, actor=actor)
    assert offer.redemption_count == 1


# --- confirm / reject / reverse --------------------------------------------


async def test_confirm_moves_reserved_to_confirmed(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor)
    customer = await _make_customer(db_session)
    redemption = await _reserve(db_session, offer=offer, customer_id=customer.id, actor=actor)

    order = await _make_order(db_session, customer_id=customer.id)
    confirmed = await redemptions.confirm(
        db_session, redemption=redemption, order_id=order.id, actor=actor
    )
    assert confirmed.status == "confirmed"
    assert confirmed.order_id == order.id
    assert confirmed.confirmed_at is not None


async def test_reject_releases_capacity_and_requires_reserved_status(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor)
    customer = await _make_customer(db_session)
    redemption = await _reserve(db_session, offer=offer, customer_id=customer.id, actor=actor)
    assert offer.redemption_count == 1

    rejected = await redemptions.reject(
        db_session, redemption=redemption, reason="customer cancelled", actor=actor
    )
    assert rejected.status == "rejected"
    assert offer.redemption_count == 0

    with pytest.raises(InvalidRedemptionStateError):
        await redemptions.reject(db_session, redemption=rejected, reason="again", actor=actor)


async def test_reject_on_confirmed_redemption_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor)
    customer = await _make_customer(db_session)
    redemption = await _reserve(db_session, offer=offer, customer_id=customer.id, actor=actor)
    order = await _make_order(db_session, customer_id=customer.id)
    confirmed = await redemptions.confirm(
        db_session, redemption=redemption, order_id=order.id, actor=actor
    )
    with pytest.raises(InvalidRedemptionStateError):
        await redemptions.reject(db_session, redemption=confirmed, reason="too late", actor=actor)


async def test_reverse_releases_capacity_from_confirmed_redemption(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor)
    customer = await _make_customer(db_session)
    redemption = await _reserve(db_session, offer=offer, customer_id=customer.id, actor=actor)
    order = await _make_order(db_session, customer_id=customer.id)
    confirmed = await redemptions.confirm(
        db_session, redemption=redemption, order_id=order.id, actor=actor
    )
    assert offer.redemption_count == 1

    reversed_redemption = await redemptions.reverse(
        db_session, redemption=confirmed, reason="refund", actor=actor
    )
    assert reversed_redemption.status == "reversed"
    assert reversed_redemption.reversed_at is not None
    assert offer.redemption_count == 0


async def test_reverse_requires_confirmed_status(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor)
    customer = await _make_customer(db_session)
    redemption = await _reserve(db_session, offer=offer, customer_id=customer.id, actor=actor)
    with pytest.raises(InvalidRedemptionStateError):
        await redemptions.reverse(db_session, redemption=redemption, reason="refund", actor=actor)


# --- Coupon-gated offers -----------------------------------------------------


async def _make_coupon(
    session: AsyncSession,
    *,
    offer: Offer,
    actor: StaffUser,
    is_reusable: bool = True,
    is_active_override: bool | None = None,
    expires_at: datetime | None = None,
) -> Coupon:
    coupon = await coupons_service.create_coupon(
        session,
        offer=offer,
        payload=CouponCreateIn(
            code=f"CODE{uuid.uuid4().hex[:8].upper()}",
            is_reusable=is_reusable,
            expires_at=expires_at,
        ),
        actor=actor,
    )
    if is_active_override is not None:
        coupon.is_active = is_active_override
        await session.flush()
    return coupon


async def test_reserve_without_coupon_code_when_required_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor, requires_code=True)
    customer = await _make_customer(db_session)
    with pytest.raises(NotEligibleError, match="coupon_code_required"):
        await _reserve(db_session, offer=offer, customer_id=customer.id, actor=actor)


async def test_reserve_with_inactive_coupon_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor, requires_code=True)
    coupon = await _make_coupon(db_session, offer=offer, actor=actor, is_active_override=False)
    customer = await _make_customer(db_session)
    with pytest.raises(NotEligibleError, match="coupon_inactive"):
        await _reserve(
            db_session, offer=offer, customer_id=customer.id, coupon_code=coupon.code, actor=actor
        )


async def test_reserve_with_expired_coupon_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor, requires_code=True)
    coupon = await _make_coupon(
        db_session, offer=offer, actor=actor, expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    customer = await _make_customer(db_session)
    with pytest.raises(NotEligibleError, match="coupon_expired"):
        await _reserve(
            db_session, offer=offer, customer_id=customer.id, coupon_code=coupon.code, actor=actor
        )


async def test_reserve_with_valid_reusable_coupon_succeeds_and_increments_count(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor, requires_code=True)
    coupon = await _make_coupon(db_session, offer=offer, actor=actor, is_reusable=True)
    customer = await _make_customer(db_session)

    redemption = await _reserve(
        db_session, offer=offer, customer_id=customer.id, coupon_code=coupon.code, actor=actor
    )
    assert redemption.status == "reserved"
    assert redemption.coupon_id == coupon.id
    assert coupon.redemption_count == 1


async def test_reusable_coupon_can_be_used_by_a_second_customer(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor, requires_code=True)
    coupon = await _make_coupon(db_session, offer=offer, actor=actor, is_reusable=True)
    first_customer = await _make_customer(db_session)
    second_customer = await _make_customer(db_session)

    await _reserve(
        db_session, offer=offer, customer_id=first_customer.id, coupon_code=coupon.code, actor=actor
    )
    await _reserve(
        db_session,
        offer=offer,
        customer_id=second_customer.id,
        coupon_code=coupon.code,
        actor=actor,
    )
    assert coupon.redemption_count == 2


async def test_single_use_coupon_can_only_be_used_once(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    offer = await _make_active_offer(db_session, actor=actor, requires_code=True)
    coupon = await _make_coupon(db_session, offer=offer, actor=actor, is_reusable=False)
    first_customer = await _make_customer(db_session)
    second_customer = await _make_customer(db_session)

    await _reserve(
        db_session, offer=offer, customer_id=first_customer.id, coupon_code=coupon.code, actor=actor
    )
    assert coupon.redemption_count == 1

    with pytest.raises(NotEligibleError, match="coupon_already_used"):
        await _reserve(
            db_session,
            offer=offer,
            customer_id=second_customer.id,
            coupon_code=coupon.code,
            actor=actor,
        )
    assert coupon.redemption_count == 1  # still only used once
