"""The append-only points ledger and its balance projection.

**This is the only module permitted to insert into `loyalty_ledger_entries`
or mutate `loyalty_accounts.points_balance`/lifetime counters.** Mirrors
`app.inventory.ledger`'s guarantees exactly (DATABASE_AND_API.md section
9.3, reused here for GROWTH_AND_INTELLIGENCE.md section 5.4's identical
requirements): every entry is signed, idempotency-keyed, and the balance
row is locked with `SELECT ... FOR UPDATE` before being adjusted so two
concurrent transactions touching the same account serialize rather than
losing one of the two deltas.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.db.models import LoyaltyAccount, LoyaltyLedgerEntry
from app.db.models.loyalty_ledger_entry import EARN_ENTRY_TYPES, REDEEM_ENTRY_TYPES
from app.loyalty.errors import (
    AlreadyReversedError,
    DuplicateIdempotencyKeyError,
    InsufficientPointsError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def find_by_idempotency_key(
    session: AsyncSession, idempotency_key: str
) -> LoyaltyLedgerEntry | None:
    result: LoyaltyLedgerEntry | None = await session.scalar(
        select(LoyaltyLedgerEntry).where(LoyaltyLedgerEntry.idempotency_key == idempotency_key)
    )
    return result


async def _lock_account(session: AsyncSession, account_id: uuid.UUID) -> LoyaltyAccount:
    account = await session.scalar(
        select(LoyaltyAccount).where(LoyaltyAccount.id == account_id).with_for_update()
    )
    if account is None:
        raise ValueError(f"Loyalty account {account_id} not found.")
    return account


async def post_entry(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    entry_type: str,
    points: int,
    idempotency_key: str,
    actor_id: uuid.UUID | None,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    description: str | None = None,
    effective_at: datetime | None = None,
    expiry_at: datetime | None = None,
    approval_reference: str | None = None,
    metadata: dict[str, Any] | None = None,
    is_credit: bool | None = None,
) -> LoyaltyLedgerEntry:
    """Post one ledger entry and update the account projection, atomically.

    `points` is always a POSITIVE magnitude; the sign is derived from
    `entry_type` the same way `app.inventory.ledger.post_movement` derives
    stock direction from `movement_type` — callers cannot accidentally
    double-negate a redemption.

    `is_credit` is required, and only meaningful, for `entry_type ==
    "correction"`, whose direction isn't fixed by the type itself (a
    correction can raise or lower a balance) — the same treatment
    `app.inventory.ledger.post_movement`'s `is_increase` gives
    `stock_count_adjustment`.
    """
    if points <= 0:
        raise ValueError(f"post_entry expects a positive magnitude; got {points}.")

    existing = await find_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        raise DuplicateIdempotencyKeyError(
            f"A loyalty ledger entry with idempotency key {idempotency_key!r} already exists; "
            "the operation was not applied twice."
        )

    if entry_type in EARN_ENTRY_TYPES:
        signed = points
    elif entry_type in REDEEM_ENTRY_TYPES or entry_type == "expire":
        signed = -points
    elif entry_type == "correction":
        if is_credit is None:
            raise ValueError("entry_type='correction' requires is_credit to be set.")
        signed = points if is_credit else -points
    else:
        # reverse_earn/reverse_redemption/merge_transfer are only ever
        # produced internally by reverse_entry()/merge helpers, which pass
        # their own already-signed direction through the private path
        # below — never reachable from post_entry's public callers.
        signed = points

    account = await _lock_account(session, account_id)
    new_balance = account.points_balance + signed
    if new_balance < 0:
        raise InsufficientPointsError(
            f"Account {account.account_number}: {abs(signed)} points required but only "
            f"{account.points_balance} available."
        )

    account.points_balance = new_balance
    if signed > 0 and entry_type in EARN_ENTRY_TYPES:
        account.lifetime_points_earned += signed
    elif entry_type in REDEEM_ENTRY_TYPES:
        account.lifetime_points_redeemed += points
    elif entry_type == "expire":
        account.lifetime_points_expired += points

    now = effective_at or datetime.now(UTC)
    entry = LoyaltyLedgerEntry(
        id=uuid.uuid4(),
        account_id=account_id,
        entry_type=entry_type,
        points_delta=signed,
        balance_after=new_balance,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        description=description,
        effective_at=now,
        expiry_at=expiry_at,
        remaining_in_lot=points if entry_type in EARN_ENTRY_TYPES and expiry_at else None,
        created_by=actor_id,
        approval_reference=approval_reference,
        entry_metadata=metadata,
    )
    session.add(entry)
    await session.flush()
    return entry


async def reverse_entry(
    session: AsyncSession,
    *,
    original: LoyaltyLedgerEntry,
    actor_id: uuid.UUID | None,
    reason: str,
    idempotency_key: str,
) -> LoyaltyLedgerEntry:
    """Post a compensating entry for `original`. The original row is never
    edited beyond its reversal-bookkeeping pointer — the ledger keeps both
    the original fact and its correction."""
    if original.reversed_by_id is not None:
        raise AlreadyReversedError(f"Ledger entry {original.id} was already reversed.")

    existing = await find_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        raise DuplicateIdempotencyKeyError(
            f"A loyalty ledger entry with idempotency key {idempotency_key!r} already exists."
        )

    reversal_type = "reverse_earn" if original.points_delta > 0 else "reverse_redemption"
    signed = -original.points_delta

    account = await _lock_account(session, original.account_id)
    new_balance = account.points_balance + signed
    if new_balance < 0:
        raise InsufficientPointsError(
            f"Reversing entry {original.id} would take the balance to {new_balance}; "
            "those points have already been spent."
        )
    account.points_balance = new_balance
    if signed > 0:
        account.lifetime_points_redeemed = max(0, account.lifetime_points_redeemed - abs(signed))
    else:
        account.lifetime_points_earned = max(0, account.lifetime_points_earned - abs(signed))

    now = datetime.now(UTC)
    reversal = LoyaltyLedgerEntry(
        id=uuid.uuid4(),
        account_id=original.account_id,
        entry_type=reversal_type,
        points_delta=signed,
        balance_after=new_balance,
        source_type=original.source_type,
        source_id=original.source_id,
        idempotency_key=idempotency_key,
        description=reason,
        effective_at=now,
        reversal_of_id=original.id,
        created_by=actor_id,
    )
    session.add(reversal)
    await session.flush()

    original.reversed_by_id = reversal.id
    await session.flush()
    return reversal
