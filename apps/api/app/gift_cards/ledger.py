"""The append-only gift card balance ledger — GROWTH_AND_INTELLIGENCE.md
section 9.4/9.5. Mirrors `app.loyalty.ledger`'s guarantees exactly:
signed entries, idempotency keys, and `SELECT ... FOR UPDATE` locking
before any balance mutation so concurrent redemptions against the same
remaining balance serialize rather than both succeeding.

**This is the only module permitted to insert into
`gift_card_ledger_entries` or mutate `gift_cards.current_balance_minor`.**
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.db.models import GiftCard, GiftCardLedgerEntry
from app.gift_cards.errors import (
    AlreadyReversedError,
    DuplicateIdempotencyKeyError,
    InsufficientBalanceError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_CREDIT_ENTRY_TYPES = ("issue",)
_DEBIT_ENTRY_TYPES = ("redeem", "expire", "cancel")


def status_for_balance(*, initial_amount_minor: int, balance_minor: int) -> str:
    if balance_minor <= 0:
        return "fully_redeemed"
    if balance_minor < initial_amount_minor:
        return "partially_redeemed"
    return "active"


async def find_by_idempotency_key(
    session: AsyncSession, idempotency_key: str
) -> GiftCardLedgerEntry | None:
    result: GiftCardLedgerEntry | None = await session.scalar(
        select(GiftCardLedgerEntry).where(GiftCardLedgerEntry.idempotency_key == idempotency_key)
    )
    return result


async def lock_card(session: AsyncSession, gift_card_id: uuid.UUID) -> GiftCard:
    card = await session.scalar(
        select(GiftCard).where(GiftCard.id == gift_card_id).with_for_update()
    )
    if card is None:
        raise ValueError(f"Gift card {gift_card_id} not found.")
    return card


async def post_entry(
    session: AsyncSession,
    *,
    gift_card_id: uuid.UUID,
    entry_type: str,
    amount_minor: int,
    idempotency_key: str,
    actor_id: uuid.UUID | None,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    reason: str | None = None,
    is_credit: bool | None = None,
    update_status: bool = True,
    effective_at: datetime | None = None,
) -> GiftCardLedgerEntry:
    """`amount_minor` is always a POSITIVE magnitude; sign is derived from
    `entry_type`, with `is_credit` required for `entry_type == "adjust"` —
    same escape hatch as `app.loyalty.ledger.post_entry`."""
    if amount_minor <= 0:
        raise ValueError(f"post_entry expects a positive magnitude; got {amount_minor}.")

    existing = await find_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        raise DuplicateIdempotencyKeyError(
            f"A gift card ledger entry with idempotency key {idempotency_key!r} already exists; "
            "the operation was not applied twice."
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
        # directly.
        signed = amount_minor

    card = await lock_card(session, gift_card_id)
    new_balance = card.current_balance_minor + signed
    if new_balance < 0:
        raise InsufficientBalanceError(
            f"Gift card {card.card_number}: {abs(signed)} minor units required but only "
            f"{card.current_balance_minor} available."
        )
    if new_balance > card.initial_amount_minor:
        new_balance = card.initial_amount_minor

    card.current_balance_minor = new_balance
    if update_status and card.status not in ("draft", "expired", "cancelled", "suspended"):
        card.status = status_for_balance(
            initial_amount_minor=card.initial_amount_minor, balance_minor=new_balance
        )

    now = effective_at or datetime.now(UTC)
    entry = GiftCardLedgerEntry(
        id=uuid.uuid4(),
        gift_card_id=gift_card_id,
        entry_type=entry_type,
        amount_delta_minor=signed,
        balance_after_minor=new_balance,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        reason=reason,
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
    original: GiftCardLedgerEntry,
    actor_id: uuid.UUID | None,
    reason: str,
    idempotency_key: str,
) -> GiftCardLedgerEntry:
    if original.reversal_of_id is not None:
        raise AlreadyReversedError(f"Ledger entry {original.id} is itself a reversal.")
    already_reversed = await session.scalar(
        select(GiftCardLedgerEntry).where(GiftCardLedgerEntry.reversal_of_id == original.id)
    )
    if already_reversed is not None:
        raise AlreadyReversedError(f"Ledger entry {original.id} was already reversed.")

    existing = await find_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        raise DuplicateIdempotencyKeyError(
            f"A gift card ledger entry with idempotency key {idempotency_key!r} already exists."
        )

    signed = -original.amount_delta_minor
    card = await lock_card(session, original.gift_card_id)
    new_balance = card.current_balance_minor + signed
    if new_balance < 0:
        raise InsufficientBalanceError(
            f"Reversing entry {original.id} would take the balance to {new_balance}; "
            "that value has already been redeemed further."
        )
    if new_balance > card.initial_amount_minor:
        new_balance = card.initial_amount_minor

    card.current_balance_minor = new_balance
    if card.status not in ("draft", "expired", "cancelled", "suspended"):
        card.status = status_for_balance(
            initial_amount_minor=card.initial_amount_minor, balance_minor=new_balance
        )

    now = datetime.now(UTC)
    reversal = GiftCardLedgerEntry(
        id=uuid.uuid4(),
        gift_card_id=original.gift_card_id,
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
