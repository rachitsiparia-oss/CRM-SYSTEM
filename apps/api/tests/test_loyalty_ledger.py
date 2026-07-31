"""Domain/service-level tests for the loyalty module —
`app.loyalty.ledger`, `app.loyalty.accounts`, and `app.loyalty.programs`.

Mirrors `test_inventory_ledger.py`'s pattern exactly (this ledger was
explicitly built to reuse `app.inventory.ledger`'s guarantees): every entry
is signed, idempotency-keyed, negative balances are refused, and reversal
is a compensating entry rather than an edit. Also covers the program/tier
configuration state machine and automatic tier evaluation that sit above
the ledger.
"""

import uuid
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

import pytest
from app.db.models import Customer, LoyaltyAccount, LoyaltyProgram, LoyaltyTier, StaffUser
from app.loyalty import accounts as accounts_service
from app.loyalty import ledger
from app.loyalty import programs as programs_service
from app.loyalty.errors import (
    AlreadyReversedError,
    DuplicateIdempotencyKeyError,
    InsufficientPointsError,
    InvalidStatusTransitionError,
)
from app.loyalty.schemas import EnrollIn, ProgramCreateIn, TierCreateIn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


# --- Fixture-data helpers ----------------------------------------------------


async def make_customer(session: AsyncSession, **overrides: object) -> Customer:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": f"Customer {suffix}",
        "first_name": "Test",
        "last_name": "Customer",
    }
    fields.update(overrides)
    customer = Customer(**fields)
    session.add(customer)
    await session.flush()
    return customer


async def make_active_program(
    session: AsyncSession, *, actor: StaffUser, **overrides: Any
) -> LoyaltyProgram:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, Any] = {
        "code": f"program-{suffix}",
        "name": f"Program {suffix}",
    }
    fields.update(overrides)
    program = await programs_service.create_program(
        session, actor=actor, payload=ProgramCreateIn(**fields)
    )
    return await programs_service.transition_program(
        session, actor=actor, program=program, target_status="active"
    )


async def make_tier(
    session: AsyncSession, *, actor: StaffUser, program: LoyaltyProgram, **overrides: Any
) -> LoyaltyTier:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, Any] = {
        "code": f"tier-{suffix}",
        "name": f"Tier {suffix}",
        "rank": 1,
        "qualification_metric": "manual",
        "threshold": Decimal("0"),
    }
    fields.update(overrides)
    return await programs_service.create_tier(
        session, actor=actor, program=program, payload=TierCreateIn(**fields)
    )


async def make_account(
    session: AsyncSession, *, actor: StaffUser, customer: Customer, program: LoyaltyProgram
) -> LoyaltyAccount:
    return await accounts_service.enroll(
        session, actor=actor, payload=EnrollIn(customer_id=customer.id, program_id=program.id)
    )


def _idem() -> str:
    return f"idem-{uuid.uuid4().hex}"


# --- Program configuration state machine -------------------------------------


async def test_program_starts_in_draft_status(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    suffix = uuid.uuid4().hex[:10]
    program = await programs_service.create_program(
        db_session,
        actor=actor,
        payload=ProgramCreateIn(code=f"program-{suffix}", name=f"Program {suffix}"),
    )
    assert program.status == "draft"


async def test_transition_draft_to_active_succeeds(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    program = await make_active_program(db_session, actor=actor)
    assert program.status == "active"
    assert program.activated_at is not None


async def test_transition_rejects_invalid_target(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    suffix = uuid.uuid4().hex[:10]
    program = await programs_service.create_program(
        db_session,
        actor=actor,
        payload=ProgramCreateIn(code=f"program-{suffix}", name=f"Program {suffix}"),
    )
    # draft -> paused is not an allowed transition (only active/archived are).
    with pytest.raises(InvalidStatusTransitionError):
        await programs_service.transition_program(
            db_session, actor=actor, program=program, target_status="paused"
        )


async def test_transition_rejects_leaving_archived(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    program = await make_active_program(db_session, actor=actor)
    program = await programs_service.transition_program(
        db_session, actor=actor, program=program, target_status="archived"
    )
    assert program.archived_at is not None
    with pytest.raises(InvalidStatusTransitionError):
        await programs_service.transition_program(
            db_session, actor=actor, program=program, target_status="active"
        )


async def test_create_tier_for_program(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    program = await make_active_program(db_session, actor=actor)
    tier = await make_tier(
        db_session,
        actor=actor,
        program=program,
        code="gold",
        name="Gold",
        rank=2,
        qualification_metric="lifetime_spend",
        threshold=Decimal("5000"),
    )
    assert tier.program_id == program.id
    assert tier.qualification_metric == "lifetime_spend"
    assert tier.threshold == Decimal("5000.00")


# --- Account enrollment -------------------------------------------------------


async def test_enroll_is_idempotent_per_customer_program(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)

    first = await accounts_service.enroll(
        db_session, actor=actor, payload=EnrollIn(customer_id=customer.id, program_id=program.id)
    )
    second = await accounts_service.enroll(
        db_session, actor=actor, payload=EnrollIn(customer_id=customer.id, program_id=program.id)
    )
    assert first.id == second.id


# --- post_entry sign derivation -----------------------------------------------


async def test_earn_order_increases_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)

    entry = await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="earn_order",
        points=100,
        idempotency_key=_idem(),
        actor_id=actor.id,
    )
    assert entry.points_delta == 100
    await db_session.refresh(account)
    assert account.points_balance == 100
    assert account.lifetime_points_earned == 100


async def test_earn_manual_increases_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)

    entry = await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="earn_manual",
        points=40,
        idempotency_key=_idem(),
        actor_id=actor.id,
    )
    assert entry.points_delta == 40
    await db_session.refresh(account)
    assert account.points_balance == 40


async def test_redeem_order_decreases_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)
    await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="earn_order",
        points=100,
        idempotency_key=_idem(),
        actor_id=actor.id,
    )

    entry = await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="redeem_order",
        points=40,
        idempotency_key=_idem(),
        actor_id=actor.id,
    )
    assert entry.points_delta == -40
    await db_session.refresh(account)
    assert account.points_balance == 60
    assert account.lifetime_points_redeemed == 40


async def test_correction_requires_is_credit(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)

    with pytest.raises(ValueError):
        await ledger.post_entry(
            db_session,
            account_id=account.id,
            entry_type="correction",
            points=10,
            idempotency_key=_idem(),
            actor_id=actor.id,
        )


async def test_correction_with_is_credit_true_increases_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)

    entry = await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="correction",
        points=25,
        idempotency_key=_idem(),
        actor_id=actor.id,
        is_credit=True,
    )
    assert entry.points_delta == 25
    await db_session.refresh(account)
    assert account.points_balance == 25


async def test_correction_with_is_credit_false_decreases_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)
    await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="earn_order",
        points=50,
        idempotency_key=_idem(),
        actor_id=actor.id,
    )

    entry = await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="correction",
        points=20,
        idempotency_key=_idem(),
        actor_id=actor.id,
        is_credit=False,
    )
    assert entry.points_delta == -20
    await db_session.refresh(account)
    assert account.points_balance == 30


# --- Idempotency and insufficient balance ------------------------------------


async def test_duplicate_idempotency_key_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)
    key = _idem()

    await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="earn_order",
        points=10,
        idempotency_key=key,
        actor_id=actor.id,
    )
    with pytest.raises(DuplicateIdempotencyKeyError):
        await ledger.post_entry(
            db_session,
            account_id=account.id,
            entry_type="earn_order",
            points=10,
            idempotency_key=key,
            actor_id=actor.id,
        )
    await db_session.refresh(account)
    assert account.points_balance == 10  # not doubled


async def test_redeem_more_than_balance_raises_insufficient_points(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)

    with pytest.raises(InsufficientPointsError):
        await ledger.post_entry(
            db_session,
            account_id=account.id,
            entry_type="redeem_order",
            points=10,
            idempotency_key=_idem(),
            actor_id=actor.id,
        )


# --- Reversal ------------------------------------------------------------


async def test_reverse_entry_undoes_balance_and_marks_original(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)
    original = await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="earn_order",
        points=50,
        idempotency_key=_idem(),
        actor_id=actor.id,
    )

    await ledger.reverse_entry(
        db_session, original=original, actor_id=actor.id, reason="test", idempotency_key=_idem()
    )
    await db_session.refresh(account)
    assert account.points_balance == 0
    await db_session.refresh(original)
    assert original.reversed_by_id is not None


async def test_reverse_entry_twice_raises_already_reversed(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    program = await make_active_program(db_session, actor=actor)
    account = await make_account(db_session, actor=actor, customer=customer, program=program)
    original = await ledger.post_entry(
        db_session,
        account_id=account.id,
        entry_type="earn_order",
        points=50,
        idempotency_key=_idem(),
        actor_id=actor.id,
    )
    await ledger.reverse_entry(
        db_session, original=original, actor_id=actor.id, reason="test", idempotency_key=_idem()
    )

    with pytest.raises(AlreadyReversedError):
        await ledger.reverse_entry(
            db_session,
            original=original,
            actor_id=actor.id,
            reason="test again",
            idempotency_key=_idem(),
        )


# --- Automatic tier evaluation ------------------------------------------------


async def test_evaluate_and_apply_tier_promotes_across_threshold(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session, lifetime_value_minor=6000)
    program = await make_active_program(db_session, actor=actor)
    await make_tier(
        db_session,
        actor=actor,
        program=program,
        code="silver",
        name="Silver",
        rank=1,
        qualification_metric="lifetime_spend",
        threshold=Decimal("1000"),
    )
    gold = await make_tier(
        db_session,
        actor=actor,
        program=program,
        code="gold",
        name="Gold",
        rank=2,
        qualification_metric="lifetime_spend",
        threshold=Decimal("5000"),
    )
    account = await make_account(db_session, actor=actor, customer=customer, program=program)
    assert account.current_tier_id is None

    membership = await accounts_service.evaluate_and_apply_tier(db_session, account=account)

    assert membership is not None
    assert membership.tier_id == gold.id
    assert account.current_tier_id == gold.id


async def test_evaluate_and_apply_tier_does_not_downgrade_within_grace_window(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session, lifetime_value_minor=6000)
    program = await make_active_program(db_session, actor=actor)
    await make_tier(
        db_session,
        actor=actor,
        program=program,
        code="silver",
        name="Silver",
        rank=1,
        qualification_metric="lifetime_spend",
        threshold=Decimal("1000"),
    )
    gold = await make_tier(
        db_session,
        actor=actor,
        program=program,
        code="gold",
        name="Gold",
        rank=2,
        qualification_metric="lifetime_spend",
        threshold=Decimal("5000"),
        review_period_days=30,
    )
    account = await make_account(db_session, actor=actor, customer=customer, program=program)

    first = await accounts_service.evaluate_and_apply_tier(db_session, account=account)
    assert first is not None
    assert account.current_tier_id == gold.id
    assert account.tier_review_at is not None

    # Facts drop below gold (but still qualify for silver) while still
    # inside gold's review grace window — must not downgrade yet.
    customer.lifetime_value_minor = 2000
    await db_session.flush()

    second = await accounts_service.evaluate_and_apply_tier(db_session, account=account)
    assert second is None
    assert account.current_tier_id == gold.id
