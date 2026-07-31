"""Referral program/code/relationship service-layer tests —
`app.referrals.service` and `app.referrals.relationships`.

Covers this phase's structural anti-abuse guarantees (GROWTH_AND_INTELLIGENCE.md
section 7.4, `ReferralRelationship`'s own docstring): no self-referral, no
duplicate-referee attribution for the same normalized contact identity, one
reward-eligible order per relationship, and the reward hold period.
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.db.models import Customer, LoyaltyAccount, Order, ReferralProgram, StaffUser
from app.loyalty import programs as loyalty_programs
from app.loyalty.schemas import ProgramCreateIn as LoyaltyProgramCreateIn
from app.referrals import relationships, service
from app.referrals.errors import (
    DuplicateQualifyingOrderError,
    DuplicateRefereeError,
    MaxActiveCodesReachedError,
    RewardHoldNotElapsedError,
    SelfReferralError,
)
from app.referrals.schemas import ProgramCreateIn
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
        "status": "draft",
        "payment_status": "pending",
    }
    fields.update(overrides)
    order = Order(**fields)
    session.add(order)
    await session.flush()
    return order


async def _make_active_referral_program(
    session: AsyncSession, *, actor: StaffUser, **overrides: object
) -> ReferralProgram:
    suffix = uuid.uuid4().hex[:10]
    payload_fields: dict[str, Any] = {
        "code": f"ref-{suffix}",
        "name": "Test Referral Program",
        "referrer_reward_amount": 100,
        "referee_reward_amount": 50,
    }
    payload_fields.update(overrides)
    program = await service.create_program(
        session, actor=actor, payload=ProgramCreateIn(**payload_fields)
    )
    return await service.transition_program(
        session, actor=actor, program=program, target_status="active"
    )


async def _ensure_default_active_loyalty_program(
    session: AsyncSession, *, actor: StaffUser
) -> None:
    """Idempotent, matching `app.loyalty.seed.seed_loyalty`'s own pattern —
    reward()'s loyalty_points path enrolls through whatever the default
    active loyalty program is, so tests must not assume the DB is empty of
    one (a real environment likely already seeded `rkpr_rewards`), and must
    not create a second one (a partial unique index allows only one
    `is_default AND status = 'active'` row)."""
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


# --- issue_code -------------------------------------------------------------


async def test_issue_code_enforces_max_active_codes_per_referrer(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    program = await _make_active_referral_program(
        db_session, actor=actor, max_active_codes_per_referrer=1
    )
    referrer = await _make_customer(db_session)

    await service.issue_code(
        db_session, actor=actor, program=program, referrer_customer_id=referrer.id, expires_at=None
    )
    with pytest.raises(MaxActiveCodesReachedError):
        await service.issue_code(
            db_session,
            actor=actor,
            program=program,
            referrer_customer_id=referrer.id,
            expires_at=None,
        )


async def test_issue_code_allows_up_to_the_configured_limit(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    program = await _make_active_referral_program(
        db_session, actor=actor, max_active_codes_per_referrer=2
    )
    referrer = await _make_customer(db_session)

    first = await service.issue_code(
        db_session, actor=actor, program=program, referrer_customer_id=referrer.id, expires_at=None
    )
    second = await service.issue_code(
        db_session, actor=actor, program=program, referrer_customer_id=referrer.id, expires_at=None
    )
    assert first.id != second.id
    with pytest.raises(MaxActiveCodesReachedError):
        await service.issue_code(
            db_session,
            actor=actor,
            program=program,
            referrer_customer_id=referrer.id,
            expires_at=None,
        )


# --- attribute: self-referral and duplicate-referee anti-abuse -------------


async def test_attribute_rejects_self_referral(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    program = await _make_active_referral_program(db_session, actor=actor)
    referrer = await _make_customer(db_session)
    code = await service.issue_code(
        db_session, actor=actor, program=program, referrer_customer_id=referrer.id, expires_at=None
    )

    with pytest.raises(SelfReferralError):
        await relationships.attribute(
            db_session,
            actor=actor,
            code=code,
            referred_contact="+919876543210",
            referred_customer_id=referrer.id,
        )


async def test_attribute_rejects_duplicate_referee_identity_after_normalization(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    """Two different raw phone-number spellings that normalize to the same
    E.164 identity must collide — the whole point of normalizing before the
    identity-uniqueness check (`app.referrals.relationships.normalize_identity`,
    `ReferralRelationship`'s own docstring)."""
    actor = await make_staff_user(role_code="owner")
    program = await _make_active_referral_program(db_session, actor=actor)
    referrer = await _make_customer(db_session)
    code = await service.issue_code(
        db_session, actor=actor, program=program, referrer_customer_id=referrer.id, expires_at=None
    )

    await relationships.attribute(
        db_session,
        actor=actor,
        code=code,
        referred_contact="9876543210",
        referred_customer_id=None,
    )
    with pytest.raises(DuplicateRefereeError):
        await relationships.attribute(
            db_session,
            actor=actor,
            code=code,
            referred_contact="  98765 43210  ",
            referred_customer_id=None,
        )


async def test_normalize_identity_accepts_a_plain_email() -> None:
    """`normalize_phone` raises `NormalizationError` (not falsy) for
    anything that isn't a plausible Indian number, so `normalize_identity`
    must catch that per-format failure and fall through to email
    normalization rather than letting it propagate — a referred_contact
    that's a genuine email address with no digits (e.g.
    "alice@example.test") must resolve to its normalized email, not raise."""
    assert relationships.normalize_identity("Alice@Example.Test") == "alice@example.test"


async def test_normalize_identity_still_normalizes_a_valid_phone() -> None:
    assert relationships.normalize_identity("9876500099") == "+919876500099"


# --- qualify: duplicate qualifying order ------------------------------------


async def test_qualify_rejects_duplicate_qualifying_order(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    program = await _make_active_referral_program(db_session, actor=actor)
    referrer = await _make_customer(db_session)
    code = await service.issue_code(
        db_session, actor=actor, program=program, referrer_customer_id=referrer.id, expires_at=None
    )
    order = await _make_order(db_session)

    first_relationship = await relationships.attribute(
        db_session, actor=actor, code=code, referred_contact="9000000001", referred_customer_id=None
    )
    second_relationship = await relationships.attribute(
        db_session, actor=actor, code=code, referred_contact="9000000002", referred_customer_id=None
    )

    await relationships.qualify(
        db_session, actor=actor, relationship=first_relationship, qualifying_order_id=order.id
    )
    with pytest.raises(DuplicateQualifyingOrderError):
        await relationships.qualify(
            db_session,
            actor=actor,
            relationship=second_relationship,
            qualifying_order_id=order.id,
        )


# --- reward: hold period and dual ledger posting ----------------------------


async def test_reward_refuses_before_hold_elapsed_then_succeeds_and_posts_both_ledgers(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    await _ensure_default_active_loyalty_program(db_session, actor=actor)
    program = await _make_active_referral_program(
        db_session,
        actor=actor,
        reward_hold_days=7,
        referrer_reward_amount=120,
        referee_reward_amount=40,
    )
    referrer = await _make_customer(db_session)
    referee = await _make_customer(db_session)
    code = await service.issue_code(
        db_session, actor=actor, program=program, referrer_customer_id=referrer.id, expires_at=None
    )
    order = await _make_order(db_session, customer_id=referee.id)

    relationship = await relationships.attribute(
        db_session,
        actor=actor,
        code=code,
        referred_contact="9123456780",
        referred_customer_id=referee.id,
    )
    relationship = await relationships.qualify(
        db_session, actor=actor, relationship=relationship, qualifying_order_id=order.id
    )

    # qualified_at is "now" and reward_hold_days=7 — too soon to reward.
    with pytest.raises(RewardHoldNotElapsedError):
        await relationships.reward(db_session, actor=actor, relationship=relationship)

    # Backdate qualification past the hold window and retry.
    relationship.qualified_at = datetime.now(UTC) - timedelta(days=8)
    await db_session.flush()

    rewarded = await relationships.reward(db_session, actor=actor, relationship=relationship)
    assert rewarded.status == "rewarded"
    assert rewarded.referrer_reward_ledger_entry_id is not None
    assert rewarded.referee_reward_ledger_entry_id is not None

    referrer_account = await db_session.scalar(
        select(LoyaltyAccount).where(LoyaltyAccount.customer_id == referrer.id)
    )
    referee_account = await db_session.scalar(
        select(LoyaltyAccount).where(LoyaltyAccount.customer_id == referee.id)
    )
    assert referrer_account is not None
    assert referee_account is not None
    assert referrer_account.points_balance == 120
    assert referee_account.points_balance == 40
