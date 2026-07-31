"""Idempotent development seed data for Referrals — one active
"Refer a Friend" program (loyalty-points reward) with a code issued to a
seeded customer, so the attribution/qualify/reward flow can be exercised
end to end without fabricating a completed referral (no relationship is
pre-created — that requires a real attribution event).
"""

from __future__ import annotations

from app.db.models import Customer, ReferralCode, StaffUser
from app.referrals import service
from app.referrals.schemas import ProgramCreateIn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def seed_referrals(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    program = await service.get_program_by_code(session, "refer_a_friend")
    if program is None:
        program = await service.create_program(
            session,
            actor=actor,
            payload=ProgramCreateIn(
                code="refer_a_friend",
                name="Refer a Friend",
                referrer_eligibility_note="Any customer with an active loyalty account.",
                referee_eligibility_note="A genuinely new customer identity.",
                qualifying_order_minimum_minor=30_000,
                reward_ledger="loyalty_points",
                referrer_reward_amount=200,
                referee_reward_amount=100,
                max_active_codes_per_referrer=1,
                reward_hold_days=7,
            ),
        )
        await service.transition_program(
            session, actor=actor, program=program, target_status="active"
        )

    customer = await session.scalar(
        select(Customer).where(Customer.primary_email == "ananya.rao@example.test")
    )
    if customer is None:
        return

    existing_codes = await session.scalars(
        select(ReferralCode).where(
            ReferralCode.program_id == program.id,
            ReferralCode.referrer_customer_id == customer.id,
        )
    )
    if existing_codes.first() is not None:
        return

    await service.issue_code(
        session, actor=actor, program=program, referrer_customer_id=customer.id, expires_at=None
    )
