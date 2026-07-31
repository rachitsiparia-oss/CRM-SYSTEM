"""Idempotent development seed data for Loyalty — one default active
program with three tiers, matching PROJECT_PLAN.md's default earn rate
(1 point per ₹10) and giving the rule engine real tier data to evaluate
against. A couple of seeded Phase 5 customers are enrolled and earn a
sample order so `app.commercial_rules.facts` has non-zero loyalty facts
to read.
"""

from __future__ import annotations

from decimal import Decimal

from app.db.models import Customer, StaffUser
from app.loyalty import accounts, programs
from app.loyalty.schemas import EarnIn, EnrollIn, ProgramCreateIn, TierCreateIn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_TIERS: tuple[tuple[str, str, int, str, int], ...] = (
    ("bronze", "Bronze", 0, "manual", 0),
    ("silver", "Silver", 1, "lifetime_spend", 500_000),
    ("gold", "Gold", 2, "lifetime_spend", 1_500_000),
)

_ENROLLED_EMAILS_AND_POINTS: tuple[tuple[str, int], ...] = (
    ("ananya.rao@example.test", 250),
    ("rahul.mehta@example.test", 80),
)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def seed_loyalty(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    program = await programs.get_program_by_code(session, "rkpr_rewards")
    if program is None:
        program = await programs.create_program(
            session,
            actor=actor,
            payload=ProgramCreateIn(
                code="rkpr_rewards",
                name="RKPR Rewards",
                points_display_name="points",
                description="Earn 1 point per ₹10 spent; redeem points for order discounts.",
                points_per_currency_unit=1,
                currency_unit_minor=1000,
                redemption_points_per_unit=100,
                redemption_value_minor=2500,
                minimum_redemption_points=300,
                points_expiry_days=365,
                is_default=True,
            ),
        )
        for code, name, rank, metric, threshold in _TIERS:
            await programs.create_tier(
                session,
                actor=actor,
                program=program,
                payload=TierCreateIn(
                    code=code,
                    name=name,
                    rank=rank,
                    qualification_metric=metric,  # type: ignore[arg-type]
                    threshold=Decimal(threshold),
                    review_period_days=90 if metric != "manual" else None,
                    downgrade_grace_days=30 if metric != "manual" else None,
                ),
            )
        await programs.transition_program(
            session, actor=actor, program=program, target_status="active"
        )

    for email, points in _ENROLLED_EMAILS_AND_POINTS:
        customer = await session.scalar(select(Customer).where(Customer.primary_email == email))
        if customer is None:
            continue
        existing_account = await accounts.get_account_for_customer(
            session, customer_id=customer.id, program_id=program.id
        )
        if existing_account is not None:
            continue
        account = await accounts.enroll(
            session,
            actor=actor,
            payload=EnrollIn(
                customer_id=customer.id, program_id=program.id, enrollment_source="seed"
            ),
        )
        await accounts.earn(
            session,
            actor=actor,
            payload=EarnIn(
                account_id=account.id,
                entry_type="earn_order",
                points=points,
                idempotency_key=f"seed-earn:{account.id}",
                source_type="seed",
                description="Seed data starting balance",
            ),
        )
        await accounts.evaluate_and_apply_tier(session, account=account)
