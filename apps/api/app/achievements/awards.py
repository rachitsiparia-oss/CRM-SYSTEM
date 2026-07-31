"""Achievement evaluation and immutable award/reversal —
GROWTH_AND_INTELLIGENCE.md section 8.3/8.4. An award is created at most
once per (achievement, customer, source_event_key) — enforced by the
table's own partial unique indexes, not just service-code discipline —
and is never edited, only reversed via a compensating ledger entry.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from app.achievements.errors import (
    AchievementNotActiveError,
    AlreadyAwardedError,
    AlreadyReversedError,
    CooldownNotElapsedError,
    NotEligibleError,
)
from app.audit.service import record_audit_event
from app.commercial_rules.evaluator import evaluate
from app.commercial_rules.facts import resolve_customer_facts
from app.commercial_rules.schema import RuleNode
from app.db.models import (
    Achievement,
    CustomerAchievementAward,
    CustomerCreditLedgerEntry,
    LoyaltyLedgerEntry,
    StaffUser,
)
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_rule_node_adapter: TypeAdapter[RuleNode] = TypeAdapter(RuleNode)


def _reward_idempotency_key(
    *, achievement_id: uuid.UUID, customer_id: uuid.UUID, source_event_key: str
) -> str:
    """Both target ledgers' `idempotency_key` columns are `VARCHAR(160)`.
    `source_event_key` is caller-supplied (callers may reasonably compose
    it from multiple identifiers, e.g. an order id plus the achievement
    id) and isn't length-bounded against this specific budget, so it is
    hashed rather than embedded verbatim — the achievement/customer ids
    stay in plain UUID form for debuggability, only the part with no
    length guarantee is compressed to a fixed-size digest."""
    digest = hashlib.sha256(source_event_key.encode("utf-8")).hexdigest()
    return f"achievement:{achievement_id}:{customer_id}:{digest}"


async def get_award(session: AsyncSession, award_id: uuid.UUID) -> CustomerAchievementAward | None:
    return await session.get(CustomerAchievementAward, award_id)


async def _latest_award(
    session: AsyncSession, *, achievement_id: uuid.UUID, customer_id: uuid.UUID
) -> CustomerAchievementAward | None:
    result: CustomerAchievementAward | None = await session.scalar(
        select(CustomerAchievementAward)
        .where(
            CustomerAchievementAward.achievement_id == achievement_id,
            CustomerAchievementAward.customer_id == customer_id,
        )
        .order_by(CustomerAchievementAward.awarded_at.desc())
        .limit(1)
    )
    return result


async def evaluate_and_award(
    session: AsyncSession,
    *,
    actor: StaffUser | None,
    achievement: Achievement,
    customer_id: uuid.UUID,
    source_event_type: str,
    source_event_key: str,
) -> CustomerAchievementAward:
    if not achievement.is_active:
        raise AchievementNotActiveError(f"Achievement {achievement.code!r} is not active.")

    existing_for_event = await session.scalar(
        select(CustomerAchievementAward).where(
            CustomerAchievementAward.achievement_id == achievement.id,
            CustomerAchievementAward.customer_id == customer_id,
            CustomerAchievementAward.source_event_key == source_event_key,
        )
    )
    if existing_for_event is not None:
        raise AlreadyAwardedError(
            f"Event {source_event_key!r} already produced an award for this achievement."
        )

    latest = await _latest_award(session, achievement_id=achievement.id, customer_id=customer_id)
    if latest is not None and latest.reversed_at is None:
        if not achievement.is_repeatable:
            raise AlreadyAwardedError(
                f"Achievement {achievement.code!r} is not repeatable and was already awarded."
            )
        if achievement.cooldown_days:
            eligible_at = latest.awarded_at + timedelta(days=achievement.cooldown_days)
            now = datetime.now(UTC)
            if now < eligible_at:
                raise CooldownNotElapsedError(
                    f"Achievement {achievement.code!r} is on cooldown until "
                    f"{eligible_at.isoformat()}."
                )

    facts = await resolve_customer_facts(session, customer_id=customer_id)
    node = _rule_node_adapter.validate_python(achievement.condition)
    result = evaluate(node, facts)
    if not result.eligible:
        raise NotEligibleError(
            "Customer does not meet the achievement condition: "
            + ", ".join(result.failed_facts or result.unknown_facts or ["unmet"])
        )

    reward_entry_id: uuid.UUID | None = None
    if achievement.reward_ledger == "loyalty_points" and achievement.reward_amount:
        from app.loyalty import accounts as loyalty_accounts
        from app.loyalty import ledger as loyalty_ledger
        from app.loyalty.schemas import EnrollIn

        account = await loyalty_accounts.enroll(
            session, actor=actor, payload=EnrollIn(customer_id=customer_id)
        )
        entry = await loyalty_ledger.post_entry(
            session,
            account_id=account.id,
            entry_type="achievement_reward",
            points=achievement.reward_amount,
            idempotency_key=_reward_idempotency_key(
                achievement_id=achievement.id,
                customer_id=customer_id,
                source_event_key=source_event_key,
            ),
            actor_id=actor.id if actor else None,
            source_type="achievement",
            source_id=achievement.id,
            description=f"Achievement reward: {achievement.name}",
        )
        reward_entry_id = entry.id
    elif achievement.reward_ledger == "internal_credit" and achievement.reward_amount:
        from app.customer_credit import accounts as credit_accounts
        from app.customer_credit import ledger as credit_ledger
        from app.customer_credit.schemas import EnsureAccountIn

        credit_account = await credit_accounts.ensure_account(
            session, actor=actor, payload=EnsureAccountIn(customer_id=customer_id)
        )
        credit_entry = await credit_ledger.post_entry(
            session,
            account_id=credit_account.id,
            entry_type="issue",
            issue_reason="achievement_reward",
            amount_minor=achievement.reward_amount,
            idempotency_key=_reward_idempotency_key(
                achievement_id=achievement.id,
                customer_id=customer_id,
                source_event_key=source_event_key,
            ),
            actor_id=actor.id if actor else None,
            source_type="achievement",
            source_id=achievement.id,
            reason=f"Achievement reward: {achievement.name}",
        )
        reward_entry_id = credit_entry.id

    now = datetime.now(UTC)
    award = CustomerAchievementAward(
        id=uuid.uuid4(),
        achievement_id=achievement.id,
        customer_id=customer_id,
        source_event_type=source_event_type,
        source_event_key=source_event_key,
        is_repeatable_award=achievement.is_repeatable,
        reward_ledger_entry_id=reward_entry_id,
        awarded_at=now,
    )
    session.add(award)
    await session.flush()
    if actor is not None:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="achievement.awarded",
            target_type="customer_achievement_award",
            target_id=award.id,
            safe_metadata={"achievement_id": str(achievement.id), "customer_id": str(customer_id)},
        )
    return award


async def reverse_award(
    session: AsyncSession,
    *,
    actor: StaffUser,
    award: CustomerAchievementAward,
    achievement: Achievement,
    reason: str,
) -> CustomerAchievementAward:
    if award.reversed_at is not None:
        raise AlreadyReversedError(f"Award {award.id} was already reversed.")

    if award.reward_ledger_entry_id is not None:
        if achievement.reward_ledger == "loyalty_points":
            from app.loyalty import ledger as loyalty_ledger

            original = await session.get(LoyaltyLedgerEntry, award.reward_ledger_entry_id)
            if original is not None:
                await loyalty_ledger.reverse_entry(
                    session,
                    original=original,
                    actor_id=actor.id,
                    reason=reason,
                    idempotency_key=f"achievement-reverse:{award.id}",
                )
        elif achievement.reward_ledger == "internal_credit":
            from app.customer_credit import ledger as credit_ledger

            credit_original = await session.get(
                CustomerCreditLedgerEntry, award.reward_ledger_entry_id
            )
            if credit_original is not None:
                await credit_ledger.reverse_entry(
                    session,
                    original=credit_original,
                    actor_id=actor.id,
                    reason=reason,
                    idempotency_key=f"achievement-reverse:{award.id}",
                )

    award.reversed_at = datetime.now(UTC)
    award.reversal_reason = reason
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="achievement.award_reversed",
        target_type="customer_achievement_award",
        target_id=award.id,
        safe_metadata={"reason": reason},
    )
    return award
