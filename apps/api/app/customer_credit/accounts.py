"""Customer credit account lookup/ensure and issue/redeem/adjust/reverse
wrappers around the ledger — GROWTH_AND_INTELLIGENCE.md section 10."""

from __future__ import annotations

import uuid

from app.audit.service import record_audit_event
from app.customer_credit import ledger as ledger_service
from app.customer_credit.errors import AccountNotActiveError
from app.customer_credit.schemas import AdjustIn, EnsureAccountIn, IssueIn, RedeemIn, ReverseIn
from app.db.models import CustomerCreditAccount, CustomerCreditLedgerEntry, StaffUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_account(session: AsyncSession, account_id: uuid.UUID) -> CustomerCreditAccount | None:
    return await session.get(CustomerCreditAccount, account_id)


async def get_account_for_customer(
    session: AsyncSession, customer_id: uuid.UUID
) -> CustomerCreditAccount | None:
    result: CustomerCreditAccount | None = await session.scalar(
        select(CustomerCreditAccount).where(CustomerCreditAccount.customer_id == customer_id)
    )
    return result


async def ensure_account(
    session: AsyncSession, *, actor: StaffUser | None, payload: EnsureAccountIn
) -> CustomerCreditAccount:
    existing = await get_account_for_customer(session, payload.customer_id)
    if existing is not None:
        return existing

    account = CustomerCreditAccount(
        id=uuid.uuid4(), customer_id=payload.customer_id, status="active", current_balance_minor=0
    )
    session.add(account)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id if actor else None,
        action_code="customer_credit.account.created",
        target_type="customer_credit_account",
        target_id=account.id,
        safe_metadata={"customer_id": str(payload.customer_id)},
    )
    return account


async def issue(
    session: AsyncSession, *, actor: StaffUser, payload: IssueIn
) -> CustomerCreditLedgerEntry:
    account = await get_account(session, payload.account_id)
    if account is None:
        raise AccountNotActiveError(f"Customer credit account {payload.account_id} not found.")
    if account.status != "active":
        raise AccountNotActiveError(f"Customer credit account {account.id} is {account.status!r}.")

    entry = await ledger_service.post_entry(
        session,
        account_id=payload.account_id,
        entry_type="issue",
        amount_minor=payload.amount_minor,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id,
        issue_reason=payload.issue_reason,
        source_type=payload.source_type,
        source_id=payload.source_id,
        reason=payload.reason,
        approval_reference=payload.approval_reference,
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer_credit.issued",
        target_type="customer_credit_ledger_entry",
        target_id=entry.id,
        safe_metadata={"amount_minor": payload.amount_minor, "issue_reason": payload.issue_reason},
    )
    return entry


async def redeem(
    session: AsyncSession, *, actor: StaffUser | None, payload: RedeemIn
) -> CustomerCreditLedgerEntry:
    entry = await ledger_service.post_entry(
        session,
        account_id=payload.account_id,
        entry_type="redeem",
        amount_minor=payload.amount_minor,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id if actor else None,
        source_type=payload.source_type,
        source_id=payload.source_id,
        reason=payload.reason,
    )
    if actor is not None:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="customer_credit.redeemed",
            target_type="customer_credit_ledger_entry",
            target_id=entry.id,
            safe_metadata={"amount_minor": payload.amount_minor},
        )
    return entry


async def adjust(
    session: AsyncSession, *, actor: StaffUser, payload: AdjustIn
) -> CustomerCreditLedgerEntry:
    magnitude = abs(payload.amount_delta_minor)
    entry = await ledger_service.post_entry(
        session,
        account_id=payload.account_id,
        entry_type="adjust",
        amount_minor=magnitude,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id,
        reason=payload.reason,
        approval_reference=payload.approval_reference,
        is_credit=payload.amount_delta_minor > 0,
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer_credit.adjusted",
        target_type="customer_credit_ledger_entry",
        target_id=entry.id,
        safe_metadata={"amount_delta_minor": payload.amount_delta_minor, "reason": payload.reason},
    )
    return entry


async def reverse(
    session: AsyncSession, *, actor: StaffUser, payload: ReverseIn
) -> CustomerCreditLedgerEntry:
    original = await session.get(CustomerCreditLedgerEntry, payload.entry_id)
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
        action_code="customer_credit.reversed",
        target_type="customer_credit_ledger_entry",
        target_id=reversal.id,
        safe_metadata={"original_entry_id": str(original.id), "reason": payload.reason},
    )
    return reversal


async def list_ledger(
    session: AsyncSession, *, account_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[CustomerCreditLedgerEntry], int]:
    total = await session.scalar(
        select(func.count())
        .select_from(CustomerCreditLedgerEntry)
        .where(CustomerCreditLedgerEntry.account_id == account_id)
    )
    rows = await session.scalars(
        select(CustomerCreditLedgerEntry)
        .where(CustomerCreditLedgerEntry.account_id == account_id)
        .order_by(CustomerCreditLedgerEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0
