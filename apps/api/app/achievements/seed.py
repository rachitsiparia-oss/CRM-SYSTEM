"""Idempotent development seed data for Achievements — two canonical,
non-repeatable milestone achievements. Awards themselves are not seeded
(an award must come from a real triggering event, per
`app.achievements.awards`'s idempotency contract) — the order-completion
integration hook (`app.orders.commercial_growth_integration`) will award
these naturally as seeded/real orders complete.
"""

from __future__ import annotations

from app.achievements import service
from app.achievements.schemas import AchievementCreateIn
from app.commercial_rules.schema import RuleCondition
from app.db.models import StaffUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def seed_achievements(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    first_order = await service.get_achievement_by_code(session, "first_order")
    if first_order is None:
        await service.create_achievement(
            session,
            actor=actor,
            payload=AchievementCreateIn(
                code="first_order",
                name="First Order",
                description="Awarded on a customer's first completed order.",
                condition=RuleCondition(
                    fact="customer.completed_order_count", operator="gte", value=1
                ),
                reward_ledger="loyalty_points",
                reward_amount=50,
                is_repeatable=False,
            ),
        )

    big_spender = await service.get_achievement_by_code(session, "big_spender")
    if big_spender is None:
        await service.create_achievement(
            session,
            actor=actor,
            payload=AchievementCreateIn(
                code="big_spender",
                name="Big Spender",
                description="Awarded once lifetime spend crosses ₹10,000.",
                condition=RuleCondition(
                    fact="customer.lifetime_spend_minor", operator="gte", value=1_000_000
                ),
                reward_ledger="loyalty_points",
                reward_amount=200,
                is_repeatable=False,
            ),
        )
