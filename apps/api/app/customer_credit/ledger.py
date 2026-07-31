"""The append-only internal customer-credit ledger and its balance
projection — GROWTH_AND_INTELLIGENCE.md section 10.2/10.3. Mirrors
`app.loyalty.ledger`'s guarantees exactly: every entry is signed,
idempotency-keyed, and the balance row is locked with
`SELECT ... FOR UPDATE` before being adjusted. No entry type here ever
represents a cash payout, transfer, or customer top-up.

**This is the only module permitted to insert into
`customer_credit_ledger_entries` or mutate
`customer_credit_accounts.current_balance_minor`.**
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.customer_credit.errors import (
    AlreadyReversedError,
    DuplicateIdempotencyKeyError,
    InsufficientCreditError,
)
from app.db.models import CustomerCreditAccount, CustomerCreditLedgerEntry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_CREDIT_ENTRY_TYPES = ("issue",)
_DEBIT_ENTRY_TYPES = ("redeem", "expire")


async def find_by_idempotency_key(
    session: AsyncSession, idempotency_key: str
) -> CustomerCreditLedgerEntry | None:
    result: CustomerCreditLedgerEntry | None = await session.scalar(
        select(CustomerCreditLedgerEntry).where(
            CustomerCreditLedgerEntry.idempotency_key == idempotency_key
        )
    )
    return result


async def _lock_account(session: AsyncSession, account_id: uuid.UUID) -> CustomerCreditAccount:
    account = await session.scalar(
        select(CustomerCreditAccount)
        .where(CustomerCreditAccount.id == account_id)
        .with_for_update()
    )
    if account is None:
        raise ValueError(f"Customer credit account {account_id} not found.")
    return account


async def post_entry(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    entry_type: str,
    amount_minor: int,
    idempotency_key: str,
    actor_id: uuid.UUID | None,
    issue_reason: str | None = None,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    reason: str | None = None,
    approval_reference: str | None = None,
    is_credit: bool | None = None,
    effective_at: datetime | None = None,
) -> CustomerCreditLedgerEntry:
    """`amount_minor` is always a POSITIVE magnitude; the sign is derived
    from `entry_type` — mirrors `app.loyalty.ledger.post_entry` exactly,
    including the `is_credit` escape hatch for `entry_type == "adjust"`,
    whose direction isn't fixed by the type itself."""
    if amount_minor <= 0:
        raise ValueError(f"post_entry expects a positive magnitude; got {amount_minor}.")

    existing = await find_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        raise DuplicateIdempotencyKeyError(
            f"A customer credit ledger entry with idempotency key {idempotency_key!r} "
            "already exists; the operation was not applied twice."
        )

    if entry_type in _CREDIT_ENTRY_TYPES:
        signed = amount_minor
    elif entry_type in _DEBIT_ENTRY_TYPES:
        signed = -amount_minor
    elif entry_type == "adjust":
        if is_credit is None:
            raise ValueError("entry_type='adjust' requires is_credit to be set.")
        signed = amount_minor if is_credit else -amount_minor
    else:
        # 'reverse'/'migration' are produced by reverse_entry()/seed paths,
        # which pass their own already-signed direction through post_entry
        # directly — never reachable from the public earn/redeem/adjust
        # callers above.
        signed = amount_minor

    account = await _lock_account(session, account_id)
    new_balance = account.current_balance_minor + signed
    if new_balance < 0:
        raise InsufficientCreditError(
            f"Account {account.id}: {abs(signed)} minor units required but only "
            f"{account.current_balance_minor} available."
        )

    account.current_balance_minor = new_balance

    now = effective_at or datetime.now(UTC)
    entry = CustomerCreditLedgerEntry(
        id=uuid.uuid4(),
        account_id=account_id,
        entry_type=entry_type,
        issue_reason=issue_reason,
        amount_delta_minor=signed,
        balance_after_minor=new_balance,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        reason=reason,
        approval_reference=approval_reference,
        created_by=actor_id,
        effective_at=now,
        created_at=now,
    )
    session.add(entry)
    await session.flush()
    return entry


async def reverse_entry(
    session: AsyncSession,
    *,
    original: CustomerCreditLedgerEntry,
    actor_id: uuid.UUID | None,
    reason: str,
    idempotency_key: str,
) -> CustomerCreditLedgerEntry:
    if original.reversal_of_id is not None:
        raise AlreadyReversedError(f"Ledger entry {original.id} is itself a reversal.")
    already_reversed = await session.scalar(
        select(CustomerCreditLedgerEntry).where(
            CustomerCreditLedgerEntry.reversal_of_id == original.id
        )
    )
    if already_reversed is not None:
        raise AlreadyReversedError(f"Ledger entry {original.id} was already reversed.")

    existing = await find_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        raise DuplicateIdempotencyKeyError(
            f"A customer credit ledger entry with idempotency key {idempotency_key!r} "
            "already exists."
        )

    signed = -original.amount_delta_minor
    account = await _lock_account(session, original.account_id)
    new_balance = account.current_balance_minor + signed
    if new_balance < 0:
        raise InsufficientCreditError(
            f"Reversing entry {original.id} would take the balance to {new_balance}; "
            "that credit has already been spent."
        )
    account.current_balance_minor = new_balance

    now = datetime.now(UTC)
    reversal = CustomerCreditLedgerEntry(
        id=uuid.uuid4(),
        account_id=original.account_id,
        entry_type="reverse",
        amount_delta_minor=signed,
        balance_after_minor=new_balance,
        source_type=original.source_type,
        source_id=original.source_id,
        idempotency_key=idempotency_key,
        reason=reason,
        reversal_of_id=original.id,
        created_by=actor_id,
        effective_at=now,
        created_at=now,
    )
    session.add(reversal)
    await session.flush()
    return reversal
