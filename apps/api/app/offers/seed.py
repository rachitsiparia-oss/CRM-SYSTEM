"""Idempotent development seed data for Offers — one always-on welcome
discount (no coupon required) and one coupon-gated fixed discount, both
order-wide (no product/category scoping) to avoid coupling to specific
seeded menu items.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.commercial_rules.schema import RuleCondition
from app.db.models import StaffUser
from app.offers import coupons, service
from app.offers.benefit import FixedAmountBenefit, PercentageBenefit
from app.offers.schemas import CouponCreateIn, OfferCreateIn, OfferVersionCreateIn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def seed_offers(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    now = datetime.now(UTC)

    welcome = await service.get_offer_by_code(session, "welcome10")
    if welcome is None:
        welcome = await service.create_offer(
            session,
            actor=actor,
            payload=OfferCreateIn(
                offer_code="welcome10",
                internal_name="Welcome 10% Off",
                customer_facing_name="10% off your first order",
                offer_type="percentage_discount",
                requires_code=False,
                initial_version=OfferVersionCreateIn(
                    eligibility_rule=RuleCondition(
                        fact="customer.completed_order_count", operator="eq", value=0
                    ),
                    benefit_rule=PercentageBenefit(percent=Decimal(10)),
                    maximum_discount_minor=20_000,
                    valid_from=now,
                ),
            ),
        )
        await service.transition_offer(
            session, actor=actor, offer=welcome, target_status="in_review"
        )
        await service.transition_offer(
            session, actor=actor, offer=welcome, target_status="approved"
        )
        await service.transition_offer(session, actor=actor, offer=welcome, target_status="active")

    save100 = await service.get_offer_by_code(session, "save100")
    if save100 is None:
        save100 = await service.create_offer(
            session,
            actor=actor,
            payload=OfferCreateIn(
                offer_code="save100",
                internal_name="₹100 Off with Code",
                customer_facing_name="₹100 off with SAVE100",
                offer_type="fixed_discount",
                requires_code=True,
                initial_version=OfferVersionCreateIn(
                    eligibility_rule=RuleCondition(
                        fact="customer.lifetime_spend_minor", operator="gte", value=0
                    ),
                    benefit_rule=FixedAmountBenefit(amount_minor=10_000),
                    minimum_order_value_minor=50_000,
                    valid_from=now,
                ),
            ),
        )
        await service.transition_offer(
            session, actor=actor, offer=save100, target_status="in_review"
        )
        await service.transition_offer(
            session, actor=actor, offer=save100, target_status="approved"
        )
        await service.transition_offer(session, actor=actor, offer=save100, target_status="active")

        existing_coupon = await coupons.get_coupon_by_code(session, "SAVE100")
        if existing_coupon is None:
            await coupons.create_coupon(
                session,
                offer=save100,
                actor=actor,
                payload=CouponCreateIn(code="SAVE100", is_reusable=True),
            )
