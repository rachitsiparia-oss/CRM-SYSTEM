"""Real-DB tests for `app.achievements.awards` — evaluation-and-award,
the source_event_key idempotency anchor, the non-repeatable/repeatable +
cooldown state machine, and reward-ledger reversal on `reverse_award`.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from app.achievements import service as achievements_service
from app.achievements.awards import evaluate_and_award, reverse_award
from app.achievements.errors import (
    AchievementNotActiveError,
    AlreadyAwardedError,
    AlreadyReversedError,
    CooldownNotElapsedError,
    NotEligibleError,
)
from app.achievements.schemas import AchievementCreateIn, RewardLedger
from app.commercial_rules.schema import RuleCondition
from app.db.models import (
    Achievement,
    Customer,
    CustomerAchievementAward,
    LoyaltyProgram,
    StaffUser,
)
from app.loyalty import accounts as loyalty_accounts
from app.loyalty import programs as loyalty_programs
from app.loyalty.schemas import EnrollIn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]

# Trivially satisfiable for any freshly created customer.
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


async def _make_active_loyalty_program(session: AsyncSession) -> LoyaltyProgram:
    """Idempotent — a partial unique index allows only one `is_default AND
    status = 'active'` row, and a real environment likely already seeded one
    (`app.loyalty.seed.seed_loyalty`'s `rkpr_rewards`), so this must not
    create a second one."""
    existing = await loyalty_programs.get_default_program(session)
    if existing is not None:
        return existing
    program = LoyaltyProgram(
        id=uuid.uuid4(),
        code=f"prog-{uuid.uuid4().hex[:10]}",
        name="Test Program",
        status="active",
        is_default=True,
    )
    session.add(program)
    await session.flush()
    return program


async def _make_achievement(
    session: AsyncSession,
    *,
    actor: StaffUser,
    is_repeatable: bool = False,
    cooldown_days: int | None = None,
    reward_ledger: RewardLedger = "none",
    reward_amount: int | None = None,
) -> Achievement:
    payload = AchievementCreateIn(
        code=f"ach-{uuid.uuid4().hex[:10]}",
        name="Test Achievement",
        condition=_ALWAYS_TRUE_RULE,
        is_repeatable=is_repeatable,
        cooldown_days=cooldown_days,
        reward_ledger=reward_ledger,
        reward_amount=reward_amount,
    )
    return await achievements_service.create_achievement(session, actor=actor, payload=payload)


# --- Creating an award --------------------------------------------------


async def test_evaluate_and_award_creates_award_when_eligible(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    achievement = await _make_achievement(db_session, actor=actor)
    customer = await _make_customer(db_session)

    award = await evaluate_and_award(
        db_session,
        actor=actor,
        achievement=achievement,
        customer_id=customer.id,
        source_event_type="order.completed",
        source_event_key=f"order-{uuid.uuid4().hex}",
    )
    assert award.achievement_id == achievement.id
    assert award.customer_id == customer.id
    assert award.reversed_at is None


async def test_evaluate_and_award_requires_active_achievement(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    payload = AchievementCreateIn(
        code=f"ach-{uuid.uuid4().hex[:10]}",
        name="Inactive",
        condition=_ALWAYS_TRUE_RULE,
        is_active=False,
    )
    achievement = await achievements_service.create_achievement(
        db_session, actor=actor, payload=payload
    )
    customer = await _make_customer(db_session)

    with pytest.raises(AchievementNotActiveError):
        await evaluate_and_award(
            db_session,
            actor=actor,
            achievement=achievement,
            customer_id=customer.id,
            source_event_type="order.completed",
            source_event_key=f"order-{uuid.uuid4().hex}",
        )


async def test_evaluate_and_award_raises_when_condition_unmet(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    impossible_rule = RuleCondition(
        fact="customer.completed_order_count", operator="gte", value=999_999
    )
    payload = AchievementCreateIn(
        code=f"ach-{uuid.uuid4().hex[:10]}", name="Unreachable", condition=impossible_rule
    )
    achievement = await achievements_service.create_achievement(
        db_session, actor=actor, payload=payload
    )
    customer = await _make_customer(db_session)

    with pytest.raises(NotEligibleError):
        await evaluate_and_award(
            db_session,
            actor=actor,
            achievement=achievement,
            customer_id=customer.id,
            source_event_type="order.completed",
            source_event_key=f"order-{uuid.uuid4().hex}",
        )


# --- source_event_key idempotency --------------------------------------------


async def test_same_source_event_key_never_produces_a_second_award(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    achievement = await _make_achievement(db_session, actor=actor, is_repeatable=True)
    customer = await _make_customer(db_session)
    event_key = f"order-{uuid.uuid4().hex}"

    await evaluate_and_award(
        db_session,
        actor=actor,
        achievement=achievement,
        customer_id=customer.id,
        source_event_type="order.completed",
        source_event_key=event_key,
    )
    with pytest.raises(AlreadyAwardedError):
        await evaluate_and_award(
            db_session,
            actor=actor,
            achievement=achievement,
            customer_id=customer.id,
            source_event_type="order.completed",
            source_event_key=event_key,
        )


# --- Non-repeatable achievements ----------------------------------------


async def test_non_repeatable_achievement_rejects_second_award_even_with_new_event_key(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    achievement = await _make_achievement(db_session, actor=actor, is_repeatable=False)
    customer = await _make_customer(db_session)

    await evaluate_and_award(
        db_session,
        actor=actor,
        achievement=achievement,
        customer_id=customer.id,
        source_event_type="order.completed",
        source_event_key=f"order-{uuid.uuid4().hex}",
    )
    with pytest.raises(AlreadyAwardedError):
        await evaluate_and_award(
            db_session,
            actor=actor,
            achievement=achievement,
            customer_id=customer.id,
            source_event_type="order.completed",
            source_event_key=f"order-{uuid.uuid4().hex}",  # different key
        )


# --- Repeatable achievements with a cooldown ---------------------------------


async def test_repeatable_achievement_rejects_second_award_before_cooldown_elapses(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    achievement = await _make_achievement(
        db_session, actor=actor, is_repeatable=True, cooldown_days=7
    )
    customer = await _make_customer(db_session)

    await evaluate_and_award(
        db_session,
        actor=actor,
        achievement=achievement,
        customer_id=customer.id,
        source_event_type="order.completed",
        source_event_key=f"order-{uuid.uuid4().hex}",
    )
    with pytest.raises(CooldownNotElapsedError):
        await evaluate_and_award(
            db_session,
            actor=actor,
            achievement=achievement,
            customer_id=customer.id,
            source_event_type="order.completed",
            source_event_key=f"order-{uuid.uuid4().hex}",
        )


async def test_repeatable_achievement_succeeds_after_cooldown_elapses(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    achievement = await _make_achievement(
        db_session, actor=actor, is_repeatable=True, cooldown_days=7
    )
    customer = await _make_customer(db_session)

    first_award = await evaluate_and_award(
        db_session,
        actor=actor,
        achievement=achievement,
        customer_id=customer.id,
        source_event_type="order.completed",
        source_event_key=f"order-{uuid.uuid4().hex}",
    )

    # Backdate the previous award past the cooldown window.
    stored = await db_session.get(CustomerAchievementAward, first_award.id)
    assert stored is not None
    stored.awarded_at = datetime.now(UTC) - timedelta(days=8)
    await db_session.flush()

    second_award = await evaluate_and_award(
        db_session,
        actor=actor,
        achievement=achievement,
        customer_id=customer.id,
        source_event_type="order.completed",
        source_event_key=f"order-{uuid.uuid4().hex}",
    )
    assert second_award.id != first_award.id

    remaining = await db_session.scalars(
        select(CustomerAchievementAward).where(
            CustomerAchievementAward.achievement_id == achievement.id,
            CustomerAchievementAward.customer_id == customer.id,
        )
    )
    assert len(list(remaining)) == 2


# --- Reversal --------------------------------------------------------------


async def test_reverse_award_marks_reversed_and_restores_loyalty_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    await _make_active_loyalty_program(db_session)
    achievement = await _make_achievement(
        db_session, actor=actor, reward_ledger="loyalty_points", reward_amount=150
    )
    customer = await _make_customer(db_session)

    award = await evaluate_and_award(
        db_session,
        actor=actor,
        achievement=achievement,
        customer_id=customer.id,
        source_event_type="order.completed",
        source_event_key=f"order-{uuid.uuid4().hex}",
    )
    assert award.reward_ledger_entry_id is not None

    account = await loyalty_accounts.enroll(
        db_session, actor=actor, payload=EnrollIn(customer_id=customer.id)
    )
    await db_session.refresh(account)
    assert account.points_balance == 150

    reversed_award = await reverse_award(
        db_session, actor=actor, award=award, achievement=achievement, reason="goodwill mistake"
    )
    assert reversed_award.reversed_at is not None
    assert reversed_award.reversal_reason == "goodwill mistake"

    await db_session.refresh(account)
    assert account.points_balance == 0


async def test_reverse_award_twice_raises(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    achievement = await _make_achievement(db_session, actor=actor)
    customer = await _make_customer(db_session)

    award = await evaluate_and_award(
        db_session,
        actor=actor,
        achievement=achievement,
        customer_id=customer.id,
        source_event_type="order.completed",
        source_event_key=f"order-{uuid.uuid4().hex}",
    )
    await reverse_award(
        db_session, actor=actor, award=award, achievement=achievement, reason="oops"
    )
    with pytest.raises(AlreadyReversedError):
        await reverse_award(
            db_session, actor=actor, award=award, achievement=achievement, reason="again"
        )
