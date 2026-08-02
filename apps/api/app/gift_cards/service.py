"""Gift card issuance and status lifecycle —
GROWTH_AND_INTELLIGENCE.md section 9.2/9.3/9.6. `issue_card` is the only
place a plaintext code exists; it is returned to the caller once and
never persisted (`app.gift_cards.security`)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.audit.service import record_audit_event
from app.db.models import GiftCard, GiftCardLedgerEntry, StaffUser
from app.gift_cards import ledger as ledger_service
from app.gift_cards import security
from app.gift_cards.errors import InvalidStatusTransitionError
from app.gift_cards.schemas import AdjustGiftCardIn, IssueGiftCardIn
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_ACTIVATABLE_STATUSES = ("draft",)
_SUSPENDABLE_STATUSES = ("active", "partially_redeemed")
_CANCELLABLE_STATUSES = ("draft", "active", "partially_redeemed", "suspended")
_EXPIRABLE_STATUSES = ("active", "partially_redeemed")


async def list_gift_cards(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
) -> tuple[list[GiftCard], int]:
    query = select(GiftCard)
    count_query = select(func.count()).select_from(GiftCard)
    if status is not None:
        query = query.where(GiftCard.status == status)
        count_query = count_query.where(GiftCard.status == status)
    if customer_id is not None:
        query = query.where(
            (GiftCard.purchaser_customer_id == customer_id)
            | (GiftCard.recipient_customer_id == customer_id)
        )
        count_query = count_query.where(
            (GiftCard.purchaser_customer_id == customer_id)
            | (GiftCard.recipient_customer_id == customer_id)
        )

    total = await session.scalar(count_query)
    rows = await session.scalars(
        query.order_by(GiftCard.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rows), total or 0


async def get_gift_card(session: AsyncSession, gift_card_id: uuid.UUID) -> GiftCard | None:
    return await session.get(GiftCard, gift_card_id)


async def get_by_code(session: AsyncSession, code: str) -> GiftCard | None:
    """O(active cards) verification — `code_hash` is a salted PBKDF2 hash,
    so it cannot be looked up by equality; every active/redeemable card's
    hash is checked against the supplied code. Acceptable at RKPR's single-
    restaurant scale; if the active gift card population grows enough for
    this to matter, add a deterministic lookup prefix (e.g. HMAC of the
    code with a server-side key) without changing this function's contract.
    """
    candidates = await session.scalars(
        select(GiftCard).where(
            GiftCard.status.in_(
                ["active", "partially_redeemed", "draft", "suspended", "expired", "cancelled"]
            )
        )
    )
    for card in candidates:
        if security.verify_code(code, card.code_hash):
            return card
    return None


async def issue_card(
    session: AsyncSession, *, actor: StaffUser, payload: IssueGiftCardIn
) -> tuple[GiftCard, str]:
    plaintext_code = security.generate_code()
    code_hash = security.hash_code(plaintext_code)
    pin_hash = security.hash_pin(payload.pin) if payload.pin else None

    now = datetime.now(UTC)
    card = GiftCard(
        id=uuid.uuid4(),
        card_number=security.generate_card_number(),
        code_hash=code_hash,
        code_last4=plaintext_code[-4:],
        pin_hash=pin_hash,
        purchaser_customer_id=payload.purchaser_customer_id,
        purchaser_contact=payload.purchaser_contact,
        recipient_customer_id=payload.recipient_customer_id,
        recipient_name=payload.recipient_name,
        recipient_contact=payload.recipient_contact,
        initial_amount_minor=payload.initial_amount_minor,
        current_balance_minor=0,
        status="draft",
        issued_at=now,
        purchased_at=now if payload.purchaser_customer_id or payload.purchaser_contact else None,
        expires_at=payload.expires_at,
        source_order_id=payload.source_order_id,
        notes=payload.notes,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(card)
    await session.flush()

    await ledger_service.post_entry(
        session,
        gift_card_id=card.id,
        entry_type="issue",
        amount_minor=payload.initial_amount_minor,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id,
        source_type="order" if payload.source_order_id else "manual",
        source_id=payload.source_order_id,
        reason="Gift card issued",
        update_status=False,
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.issued",
        target_type="gift_card",
        target_id=card.id,
        safe_metadata={
            "card_number": card.card_number,
            "initial_amount_minor": card.initial_amount_minor,
        },
    )
    return card, plaintext_code


async def activate_card(session: AsyncSession, *, actor: StaffUser, card: GiftCard) -> GiftCard:
    if card.status not in _ACTIVATABLE_STATUSES:
        raise InvalidStatusTransitionError(f"Gift card {card.card_number!r} is not activatable.")
    card.status = "active"
    card.activated_at = datetime.now(UTC)
    card.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.activated",
        target_type="gift_card",
        target_id=card.id,
        safe_metadata={},
    )
    return card


async def suspend_card(
    session: AsyncSession, *, actor: StaffUser, card: GiftCard, reason: str | None
) -> GiftCard:
    if card.status not in _SUSPENDABLE_STATUSES:
        raise InvalidStatusTransitionError(f"Gift card {card.card_number!r} is not suspendable.")
    card.status = "suspended"
    card.updated_by = actor.id
    if reason:
        card.notes = f"{card.notes or ''}\nSuspended: {reason}".strip()
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.suspended",
        target_type="gift_card",
        target_id=card.id,
        safe_metadata={"reason": reason},
    )
    return card


async def reinstate_card(session: AsyncSession, *, actor: StaffUser, card: GiftCard) -> GiftCard:
    if card.status != "suspended":
        raise InvalidStatusTransitionError(f"Gift card {card.card_number!r} is not suspended.")
    card.status = ledger_service.status_for_balance(
        initial_amount_minor=card.initial_amount_minor, balance_minor=card.current_balance_minor
    )
    card.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.reinstated",
        target_type="gift_card",
        target_id=card.id,
        safe_metadata={},
    )
    return card


async def cancel_card(
    session: AsyncSession, *, actor: StaffUser, card: GiftCard, reason: str | None
) -> GiftCard:
    if card.status not in _CANCELLABLE_STATUSES:
        raise InvalidStatusTransitionError(f"Gift card {card.card_number!r} cannot be cancelled.")
    if card.current_balance_minor > 0:
        await ledger_service.post_entry(
            session,
            gift_card_id=card.id,
            entry_type="cancel",
            amount_minor=card.current_balance_minor,
            idempotency_key=f"gift-card-cancel:{card.id}",
            actor_id=actor.id,
            reason=reason or "Gift card cancelled",
            update_status=False,
        )
    card.status = "cancelled"
    card.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.cancelled",
        target_type="gift_card",
        target_id=card.id,
        safe_metadata={"reason": reason},
    )
    return card


async def expire_card(session: AsyncSession, *, actor: StaffUser, card: GiftCard) -> GiftCard:
    if card.status not in _EXPIRABLE_STATUSES:
        raise InvalidStatusTransitionError(f"Gift card {card.card_number!r} cannot be expired.")
    if card.current_balance_minor > 0:
        await ledger_service.post_entry(
            session,
            gift_card_id=card.id,
            entry_type="expire",
            amount_minor=card.current_balance_minor,
            idempotency_key=f"gift-card-expire:{card.id}",
            actor_id=actor.id,
            reason="Gift card expired",
            update_status=False,
        )
    card.status = "expired"
    card.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.expired",
        target_type="gift_card",
        target_id=card.id,
        safe_metadata={},
    )
    return card


async def expire_due_gift_cards(session: AsyncSession, *, now: datetime | None = None) -> int:
    """The Phase 15 scheduler's entry point — `expire_card` only ever ran
    one-at-a-time from `POST /gift-cards/{id}/expire`; this is the "which
    cards are due" batch selector that endpoint never needed."""
    from app.core.system_actor import get_system_actor

    now = now or datetime.now(UTC)
    system_actor = await get_system_actor(session)
    if system_actor is None:
        return 0

    due_cards = (
        await session.scalars(
            select(GiftCard).where(
                GiftCard.status.in_(_EXPIRABLE_STATUSES),
                GiftCard.expires_at.isnot(None),
                GiftCard.expires_at <= now,
            )
        )
    ).all()
    for card in due_cards:
        await expire_card(session, actor=system_actor, card=card)
    return len(due_cards)


async def adjust_card(
    session: AsyncSession, *, actor: StaffUser, card: GiftCard, payload: AdjustGiftCardIn
) -> GiftCardLedgerEntry:
    magnitude = abs(payload.amount_delta_minor)
    entry = await ledger_service.post_entry(
        session,
        gift_card_id=card.id,
        entry_type="adjust",
        amount_minor=magnitude,
        idempotency_key=payload.idempotency_key,
        actor_id=actor.id,
        reason=payload.reason,
        is_credit=payload.amount_delta_minor > 0,
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.adjusted",
        target_type="gift_card",
        target_id=card.id,
        safe_metadata={"amount_delta_minor": payload.amount_delta_minor, "reason": payload.reason},
    )
    return entry
