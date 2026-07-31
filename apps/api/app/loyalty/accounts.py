"""Account lookup/enrollment and tier evaluation/history. Ledger writes
themselves live in app.loyalty.ledger; this module is the thin
account-lifecycle layer around it.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.audit.service import record_audit_event
from app.db.models import (
    LoyaltyAccount,
    LoyaltyLedgerEntry,
    LoyaltyProgram,
    LoyaltyTier,
    LoyaltyTierMembership,
    StaffUser,
)
from app.loyalty import ledger as ledger_service
from app.loyalty import programs as programs_service
from app.loyalty.errors import ProgramNotActiveError
from app.loyalty.schemas import AdjustIn, EarnIn, EnrollIn, RedeemIn, ReverseIn
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def generate_account_number() -> str:
    return f"LYT-{uuid.uuid4().hex[:10].upper()}"


async def get_account(session: AsyncSession, account_id: uuid.UUID) -> LoyaltyAccount | None:
    return await session.get(LoyaltyAccount, account_id)


async def get_account_for_customer(
    session: AsyncSession, *, customer_id: uuid.UUID, program_id: uuid.UUID | None = None
) -> LoyaltyAccount | None:
    query = select(LoyaltyAccount).where(LoyaltyAccount.customer_id == customer_id)
    if program_id is not None:
        query = query.where(LoyaltyAccount.program_id == program_id)
    result: LoyaltyAccount | None = await session.scalar(query)
    return result


async def enroll(
    session: AsyncSession, *, actor: StaffUser | None, payload: EnrollIn
) -> LoyaltyAccount:
    program: LoyaltyProgram | None
    if payload.program_id is not None:
        program = await programs_service.get_program(session, payload.program_id)
    else:
        program = await programs_service.get_default_program(session)
    if program is None or program.status != "active":
        raise ProgramNotActiveError("No active loyalty program is available for enrollment.")

    existing = await get_account_for_customer(
        session, customer_id=payload.customer_id, program_id=program.id
    )
    if existing is not None:
        return existing

    account = LoyaltyAccount(
        id=uuid.uuid4(),
        account_number=generate_account_number(),
        customer_id=payload.customer_id,
        program_id=program.id,
        status="active",
        enrollment_source=payload.enrollment_source,
        enrolled_at=datetime.now(UTC),
    )
    session.add(account)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id if actor else None,
        action_code="loyalty.account.enrolled",
        target_type="loyalty_account",
        target_id=account.id,
        safe_metadata={"customer_id": str(payload.customer_id), "program_id": str(program.id)},
    )
    return account


async def earn(
    session: AsyncSession, *, actor: StaffUser | None, payload: EarnIn
) -> LoyaltyLedgerEntry:
    entry = await ledger_service.post_entry(
        session,
        account_id=payload.account_id,
        entry_type=payload.entry_type,
        points=payload.points,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id if actor else None,
        source_type=payload.source_type,
        source_id=payload.source_id,
        description=payload.description,
        expiry_at=payload.expiry_at,
    )
    if actor is not None:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="loyalty.points.earned",
            target_type="loyalty_ledger_entry",
            target_id=entry.id,
            safe_metadata={"points": payload.points, "entry_type": payload.entry_type},
        )
    return entry


async def redeem(
    session: AsyncSession, *, actor: StaffUser | None, payload: RedeemIn
) -> LoyaltyLedgerEntry:
    entry = await ledger_service.post_entry(
        session,
        account_id=payload.account_id,
        entry_type=payload.entry_type,
        points=payload.points,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id if actor else None,
        source_type=payload.source_type,
        source_id=payload.source_id,
        description=payload.description,
    )
    if actor is not None:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="loyalty.points.redeemed",
            target_type="loyalty_ledger_entry",
            target_id=entry.id,
            safe_metadata={"points": payload.points},
        )
    return entry


async def adjust(
    session: AsyncSession, *, actor: StaffUser, payload: AdjustIn
) -> LoyaltyLedgerEntry:
    magnitude = abs(payload.points_delta)
    entry = await ledger_service.post_entry(
        session,
        account_id=payload.account_id,
        entry_type="earn_manual" if payload.points_delta > 0 else "correction",
        points=magnitude,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id,
        description=payload.reason,
        approval_reference=payload.approval_reference,
        is_credit=payload.points_delta > 0,
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="loyalty.points.adjusted",
        target_type="loyalty_ledger_entry",
        target_id=entry.id,
        safe_metadata={"points_delta": payload.points_delta, "reason": payload.reason},
    )
    return entry


async def reverse(
    session: AsyncSession, *, actor: StaffUser, payload: ReverseIn
) -> LoyaltyLedgerEntry:
    original = await session.get(LoyaltyLedgerEntry, payload.entry_id)
    if original is None:
        raise ValueError(f"Ledger entry {payload.entry_id} not found.")
    reversal = await ledger_service.reverse_entry(
        session,
        original=original,
        actor_id=actor.id,
        reason=payload.reason,
        idempotency_key=payload.idempotency_key,
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="loyalty.ledger.reversed",
        target_type="loyalty_ledger_entry",
        target_id=reversal.id,
        safe_metadata={"original_entry_id": str(original.id), "reason": payload.reason},
    )
    return reversal


async def list_ledger(
    session: AsyncSession, *, account_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[LoyaltyLedgerEntry], int]:
    total = await session.scalar(
        select(func.count())
        .select_from(LoyaltyLedgerEntry)
        .where(LoyaltyLedgerEntry.account_id == account_id)
    )
    rows = await session.scalars(
        select(LoyaltyLedgerEntry)
        .where(LoyaltyLedgerEntry.account_id == account_id)
        .order_by(LoyaltyLedgerEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def assign_tier(
    session: AsyncSession,
    *,
    actor: StaffUser,
    account: LoyaltyAccount,
    tier: LoyaltyTier,
    reason: str,
    source: str = "manual",
) -> LoyaltyTierMembership:
    now = datetime.now(UTC)
    current = await session.scalar(
        select(LoyaltyTierMembership).where(
            LoyaltyTierMembership.account_id == account.id,
            LoyaltyTierMembership.effective_to.is_(None),
        )
    )
    if current is not None:
        current.effective_to = now

    membership = LoyaltyTierMembership(
        id=uuid.uuid4(),
        account_id=account.id,
        tier_id=tier.id,
        effective_from=now,
        source=source,
        assigned_by=actor.id,
        reason=reason,
        created_at=now,
    )
    session.add(membership)
    account.current_tier_id = tier.id
    account.tier_effective_at = now
    if tier.review_period_days:
        account.tier_review_at = now + timedelta(days=tier.review_period_days)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="loyalty.tier.assigned",
        target_type="loyalty_account",
        target_id=account.id,
        safe_metadata={"tier_id": str(tier.id), "source": source},
    )
    return membership


async def list_tier_history(
    session: AsyncSession, account_id: uuid.UUID
) -> list[LoyaltyTierMembership]:
    result = await session.scalars(
        select(LoyaltyTierMembership)
        .where(LoyaltyTierMembership.account_id == account_id)
        .order_by(LoyaltyTierMembership.effective_from.desc())
    )
    return list(result)


_METRIC_TO_FACT = {
    "lifetime_spend": "customer.lifetime_spend_minor",
    "rolling_spend": "customer.rolling_90d_spend_minor",
    "points_earned": "customer.loyalty_points_balance",
    "completed_orders": "customer.completed_order_count",
    "visits": "customer.visit_count",
}


async def evaluate_and_apply_tier(
    session: AsyncSession, *, account: LoyaltyAccount
) -> LoyaltyTierMembership | None:
    """Automatic tier evaluation — GROWTH_AND_INTELLIGENCE.md section 5.8:
    "Tier changes create history records." Only considers tiers whose
    `qualification_metric != 'manual'`; a manually-assigned tier is never
    silently overridden by this automatic pass. Picks the highest-rank
    tier the account's current facts qualify for; never downgrades below
    a tier still inside its `downgrade_grace_days` window from
    `tier_review_at`.
    """
    from app.commercial_rules.facts import resolve_customer_facts

    tiers = await programs_service.list_tiers(session, account.program_id)
    automatic_tiers = [t for t in tiers if t.qualification_metric != "manual" and t.is_active]
    if not automatic_tiers:
        return None

    facts = await resolve_customer_facts(
        session, customer_id=account.customer_id, program_id=account.program_id
    )
    qualifying: LoyaltyTier | None = None
    for tier in sorted(automatic_tiers, key=lambda t: t.rank, reverse=True):
        fact_name = _METRIC_TO_FACT.get(tier.qualification_metric)
        if fact_name is None:
            continue
        value = facts.get(fact_name)
        if value is not None and value >= tier.threshold:
            qualifying = tier
            break

    if qualifying is None or qualifying.id == account.current_tier_id:
        return None

    now = datetime.now(UTC)
    if (
        account.current_tier_id is not None
        and account.tier_review_at is not None
        and now < account.tier_review_at
    ):
        current_tier = next((t for t in tiers if t.id == account.current_tier_id), None)
        if current_tier is not None and qualifying.rank < current_tier.rank:
            # Downgrade protection: this account is still within its grace
            # window on the current (higher) tier.
            return None

    membership = LoyaltyTierMembership(
        id=uuid.uuid4(),
        account_id=account.id,
        tier_id=qualifying.id,
        effective_from=now,
        qualification_snapshot=str({k: facts.get(k) for k in _METRIC_TO_FACT.values()}),
        source="automatic",
        assigned_by=None,
        reason="Automatic tier evaluation.",
        created_at=now,
    )
    current = await session.scalar(
        select(LoyaltyTierMembership).where(
            LoyaltyTierMembership.account_id == account.id,
            LoyaltyTierMembership.effective_to.is_(None),
        )
    )
    if current is not None:
        current.effective_to = now
    session.add(membership)
    account.current_tier_id = qualifying.id
    account.tier_effective_at = now
    if qualifying.review_period_days:
        account.tier_review_at = now + timedelta(days=qualifying.review_period_days)
    await session.flush()
    return membership
