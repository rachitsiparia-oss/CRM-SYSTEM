"""Gift card redemption — GROWTH_AND_INTELLIGENCE.md section 9.5."""

from __future__ import annotations

import uuid

from app.audit.service import record_audit_event
from app.db.models import GiftCard, GiftCardLedgerEntry, StaffUser
from app.gift_cards import ledger as ledger_service
from app.gift_cards import security
from app.gift_cards.errors import (
    GiftCardNotRedeemableError,
    InvalidCodeError,
    InvalidPinError,
)
from app.gift_cards.service import get_by_code
from sqlalchemy.ext.asyncio import AsyncSession

_REDEEMABLE_STATUSES = ("active", "partially_redeemed")


async def redeem_by_code(
    session: AsyncSession,
    *,
    actor: StaffUser,
    code: str,
    pin: str | None,
    amount_minor: int,
    order_id: uuid.UUID | None,
    idempotency_key: str,
) -> GiftCardLedgerEntry:
    card = await get_by_code(session, code)
    if card is None:
        raise InvalidCodeError("Gift card code not recognized.")
    if card.pin_hash is not None and (pin is None or not security.verify_pin(pin, card.pin_hash)):
        raise InvalidPinError("Incorrect gift card PIN.")
    if card.status not in _REDEEMABLE_STATUSES:
        raise GiftCardNotRedeemableError(f"Gift card {card.card_number!r} is {card.status!r}.")

    entry = await ledger_service.post_entry(
        session,
        gift_card_id=card.id,
        entry_type="redeem",
        amount_minor=amount_minor,
        idempotency_key=idempotency_key,
        actor_id=actor.id,
        source_type="order" if order_id else "manual",
        source_id=order_id,
        reason="Gift card redemption",
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.redeemed",
        target_type="gift_card_ledger_entry",
        target_id=entry.id,
        safe_metadata={"gift_card_id": str(card.id), "amount_minor": amount_minor},
    )
    return entry


async def reverse_redemption(
    session: AsyncSession,
    *,
    actor: StaffUser,
    entry: GiftCardLedgerEntry,
    reason: str,
    idempotency_key: str,
) -> GiftCardLedgerEntry:
    reversal = await ledger_service.reverse_entry(
        session, original=entry, actor_id=actor.id, reason=reason, idempotency_key=idempotency_key
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.redemption_reversed",
        target_type="gift_card_ledger_entry",
        target_id=reversal.id,
        safe_metadata={"original_entry_id": str(entry.id), "reason": reason},
    )
    return reversal


async def get_entry(session: AsyncSession, entry_id: uuid.UUID) -> GiftCardLedgerEntry | None:
    return await session.get(GiftCardLedgerEntry, entry_id)


async def get_gift_card_for_entry(
    session: AsyncSession, entry: GiftCardLedgerEntry
) -> GiftCard | None:
    return await session.get(GiftCard, entry.gift_card_id)
