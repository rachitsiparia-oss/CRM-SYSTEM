"""Referral relationship attribution, qualification, and reward posting —
GROWTH_AND_INTELLIGENCE.md section 7.3/7.4/7.5.

Self-referral and duplicate-referee attribution are structurally
prevented by the table's own CHECK constraint and partial unique index
(`ReferralRelationship`'s docstring); the pre-checks here exist to return
a clean domain error instead of a raw integrity-constraint failure, not
as the actual enforcement mechanism.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.audit.service import record_audit_event
from app.db.models import ReferralCode, ReferralProgram, ReferralRelationship, StaffUser
from app.referrals import service as program_service
from app.referrals.errors import (
    DuplicateQualifyingOrderError,
    DuplicateRefereeError,
    InvalidRelationshipStateError,
    ProgramNotActiveError,
    RewardHoldNotElapsedError,
    SelfReferralError,
)
from app.shared.normalization import NormalizationError, normalize_email, normalize_phone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def normalize_identity(raw: str) -> str:
    """`normalize_phone`/`normalize_email` each raise `NormalizationError`
    (not return falsy) for input that doesn't match their own format —
    a referred contact may legitimately be either shape, so each is tried
    in turn and only the final fallback (neither a phone nor an email)
    falls back to a plain lowercase/stripped comparison key."""
    try:
        phone = normalize_phone(raw)
    except NormalizationError:
        phone = None
    if phone:
        return phone
    try:
        email = normalize_email(raw)
    except NormalizationError:
        email = None
    if email:
        return email
    return raw.strip().lower()


async def get_relationship(
    session: AsyncSession, relationship_id: uuid.UUID
) -> ReferralRelationship | None:
    return await session.get(ReferralRelationship, relationship_id)


async def list_relationships(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    program_id: uuid.UUID | None = None,
    status: str | None = None,
) -> tuple[list[ReferralRelationship], int]:
    query = select(ReferralRelationship)
    count_query = select(func.count()).select_from(ReferralRelationship)
    if program_id is not None:
        query = query.where(ReferralRelationship.program_id == program_id)
        count_query = count_query.where(ReferralRelationship.program_id == program_id)
    if status is not None:
        query = query.where(ReferralRelationship.status == status)
        count_query = count_query.where(ReferralRelationship.status == status)

    total = await session.scalar(count_query)
    rows = await session.scalars(
        query.order_by(ReferralRelationship.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def attribute(
    session: AsyncSession,
    *,
    actor: StaffUser,
    code: ReferralCode,
    referred_contact: str,
    referred_customer_id: uuid.UUID | None,
) -> ReferralRelationship:
    program = await program_service.get_program(session, code.program_id)
    if program is None or program.status != "active":
        raise ProgramNotActiveError("Referral program for this code is not active.")
    if not program_service.is_code_usable(code):
        raise ProgramNotActiveError("Referral code is inactive or expired.")

    if referred_customer_id is not None and referred_customer_id == code.referrer_customer_id:
        raise SelfReferralError("A customer cannot refer themselves.")

    identity_key = normalize_identity(referred_contact)
    existing = await session.scalar(
        select(ReferralRelationship).where(
            ReferralRelationship.program_id == program.id,
            ReferralRelationship.referred_identity_key == identity_key,
        )
    )
    if existing is not None:
        raise DuplicateRefereeError(
            f"Contact {identity_key!r} has already been attributed to a referral relationship."
        )

    now = datetime.now(UTC)
    relationship = ReferralRelationship(
        id=uuid.uuid4(),
        program_id=program.id,
        code_id=code.id,
        referrer_customer_id=code.referrer_customer_id,
        referred_identity_key=identity_key,
        referred_customer_id=referred_customer_id,
        attributed_at=now,
        status="attributed" if referred_customer_id else "invited",
        created_at=now,
        updated_at=now,
    )
    session.add(relationship)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="referral.attributed",
        target_type="referral_relationship",
        target_id=relationship.id,
        safe_metadata={"program_id": str(program.id)},
    )
    return relationship


async def resolve_referred_customer(
    session: AsyncSession, *, relationship: ReferralRelationship, customer_id: uuid.UUID
) -> ReferralRelationship:
    if relationship.status != "invited":
        raise InvalidRelationshipStateError(
            f"Relationship {relationship.id} is {relationship.status!r}, not 'invited'."
        )
    if customer_id == relationship.referrer_customer_id:
        raise SelfReferralError("A customer cannot refer themselves.")
    relationship.referred_customer_id = customer_id
    relationship.status = "attributed"
    await session.flush()
    return relationship


async def qualify(
    session: AsyncSession,
    *,
    actor: StaffUser,
    relationship: ReferralRelationship,
    qualifying_order_id: uuid.UUID,
) -> ReferralRelationship:
    if relationship.status not in ("invited", "attributed"):
        raise InvalidRelationshipStateError(
            f"Relationship {relationship.id} is {relationship.status!r}; cannot qualify."
        )
    existing = await session.scalar(
        select(ReferralRelationship).where(
            ReferralRelationship.qualifying_order_id == qualifying_order_id
        )
    )
    if existing is not None and existing.id != relationship.id:
        raise DuplicateQualifyingOrderError(
            f"Order {qualifying_order_id} already qualifies a different referral relationship."
        )

    now = datetime.now(UTC)
    relationship.qualifying_order_id = qualifying_order_id
    relationship.status = "qualified"
    relationship.qualified_at = now
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="referral.qualified",
        target_type="referral_relationship",
        target_id=relationship.id,
        safe_metadata={"qualifying_order_id": str(qualifying_order_id)},
    )
    return relationship


async def reject(
    session: AsyncSession, *, actor: StaffUser, relationship: ReferralRelationship, reason: str
) -> ReferralRelationship:
    if relationship.status in ("rewarded", "rejected", "cancelled"):
        raise InvalidRelationshipStateError(
            f"Relationship {relationship.id} is {relationship.status!r} and cannot be rejected."
        )
    relationship.status = "rejected"
    relationship.rejection_reason = reason
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="referral.rejected",
        target_type="referral_relationship",
        target_id=relationship.id,
        safe_metadata={"reason": reason},
    )
    return relationship


async def reward(
    session: AsyncSession, *, actor: StaffUser, relationship: ReferralRelationship
) -> ReferralRelationship:
    if relationship.status != "qualified":
        raise InvalidRelationshipStateError(
            f"Relationship {relationship.id} is {relationship.status!r}, not 'qualified'."
        )
    program = await session.get(ReferralProgram, relationship.program_id)
    if program is None:
        raise InvalidRelationshipStateError("Referral program no longer exists.")

    hold_until = (relationship.qualified_at or datetime.now(UTC)) + timedelta(
        days=program.reward_hold_days
    )
    now = datetime.now(UTC)
    if now < hold_until:
        raise RewardHoldNotElapsedError(
            f"Reward hold period ends {hold_until.isoformat()}; cannot reward yet."
        )

    if relationship.referred_customer_id is None:
        raise InvalidRelationshipStateError(
            "Relationship has no resolved referred customer; cannot reward."
        )

    referrer_entry_id: uuid.UUID
    referee_entry_id: uuid.UUID

    if program.reward_ledger == "loyalty_points":
        from app.loyalty import accounts as loyalty_accounts
        from app.loyalty import ledger as loyalty_ledger
        from app.loyalty.schemas import EnrollIn

        referrer_account = await loyalty_accounts.enroll(
            session, actor=actor, payload=EnrollIn(customer_id=relationship.referrer_customer_id)
        )
        referee_account = await loyalty_accounts.enroll(
            session, actor=actor, payload=EnrollIn(customer_id=relationship.referred_customer_id)
        )
        referrer_entry = await loyalty_ledger.post_entry(
            session,
            account_id=referrer_account.id,
            entry_type="referral_reward",
            points=program.referrer_reward_amount,
            idempotency_key=f"referral:{relationship.id}:referrer",
            actor_id=actor.id,
            source_type="referral_relationship",
            source_id=relationship.id,
            description=(
                f"Referral reward for referring customer {relationship.referred_customer_id}"
            ),
        )
        referee_entry = await loyalty_ledger.post_entry(
            session,
            account_id=referee_account.id,
            entry_type="referral_reward",
            points=program.referee_reward_amount,
            idempotency_key=f"referral:{relationship.id}:referee",
            actor_id=actor.id,
            source_type="referral_relationship",
            source_id=relationship.id,
            description="Referral welcome reward",
        )
        referrer_entry_id = referrer_entry.id
        referee_entry_id = referee_entry.id
    else:
        from app.customer_credit import accounts as credit_accounts
        from app.customer_credit import ledger as credit_ledger
        from app.customer_credit.schemas import EnsureAccountIn

        credit_referrer_account = await credit_accounts.ensure_account(
            session,
            actor=actor,
            payload=EnsureAccountIn(customer_id=relationship.referrer_customer_id),
        )
        credit_referee_account = await credit_accounts.ensure_account(
            session,
            actor=actor,
            payload=EnsureAccountIn(customer_id=relationship.referred_customer_id),
        )
        credit_referrer_entry = await credit_ledger.post_entry(
            session,
            account_id=credit_referrer_account.id,
            entry_type="issue",
            issue_reason="referral_reward",
            amount_minor=program.referrer_reward_amount,
            idempotency_key=f"referral:{relationship.id}:referrer",
            actor_id=actor.id,
            source_type="referral_relationship",
            source_id=relationship.id,
            reason="Referral reward",
        )
        credit_referee_entry = await credit_ledger.post_entry(
            session,
            account_id=credit_referee_account.id,
            entry_type="issue",
            issue_reason="referral_reward",
            amount_minor=program.referee_reward_amount,
            idempotency_key=f"referral:{relationship.id}:referee",
            actor_id=actor.id,
            source_type="referral_relationship",
            source_id=relationship.id,
            reason="Referral welcome reward",
        )
        referrer_entry_id = credit_referrer_entry.id
        referee_entry_id = credit_referee_entry.id

    relationship.referrer_reward_ledger_entry_id = referrer_entry_id
    relationship.referee_reward_ledger_entry_id = referee_entry_id
    relationship.status = "rewarded"
    relationship.rewarded_at = now
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="referral.rewarded",
        target_type="referral_relationship",
        target_id=relationship.id,
        safe_metadata={"reward_ledger": program.reward_ledger},
    )
    return relationship
