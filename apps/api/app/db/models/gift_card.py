import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 9.2 — added 2026-07-30.
GIFT_CARD_STATUSES = (
    "draft",
    "active",
    "partially_redeemed",
    "fully_redeemed",
    "expired",
    "suspended",
    "cancelled",
)


class GiftCard(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Restaurant-issued retail value, not a regulated payment instrument
    — GROWTH_AND_INTELLIGENCE.md section 9.1. `code_hash` is what uniqueness
    and lookups are keyed on; `code_last4`/`masked_display` are the only
    parts ever shown outside the `gift_cards.reveal_sensitive` permission.
    The plaintext code itself is never stored — `app.gift_cards.security`
    generates it once, returns it to the caller exactly once (at issue
    time), and persists only its hash, the same one-way pattern
    `pin_hash` already uses.
    """

    __tablename__ = "gift_cards"
    __table_args__ = (
        CheckConstraint(f"status IN {GIFT_CARD_STATUSES!r}", name="valid_status"),
        CheckConstraint("initial_amount_minor > 0", name="valid_initial_amount_minor"),
        CheckConstraint("current_balance_minor >= 0", name="valid_current_balance_minor"),
        CheckConstraint(
            "current_balance_minor <= initial_amount_minor", name="balance_not_above_initial"
        ),
        Index("uq_gift_cards_code_hash", "code_hash", unique=True),
        Index("ix_gift_cards_status", "status"),
        Index("ix_gift_cards_purchaser_customer_id", "purchaser_customer_id"),
        Index("ix_gift_cards_recipient_customer_id", "recipient_customer_id"),
    )

    card_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    code_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    pin_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    purchaser_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    purchaser_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    recipient_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    recipient_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    initial_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_balance_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True
    )
    delivery_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    delivery_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


GIFT_CARD_LEDGER_ENTRY_TYPES = (
    "issue",
    "activate",
    "redeem",
    "reverse",
    "adjust",
    "expire",
    "cancel",
    "migration",
)


class GiftCardLedgerEntry(UUIDPrimaryKeyMixin, Base):
    """Append-only, mirrors `StockMovement`/`LoyaltyLedgerEntry` — signed
    delta, idempotency key, balance-after snapshot, `app.gift_cards.ledger`
    is the only writer, corrections via `reverse`/`adjust` only.
    """

    __tablename__ = "gift_card_ledger_entries"
    __table_args__ = (
        CheckConstraint(f"entry_type IN {GIFT_CARD_LEDGER_ENTRY_TYPES!r}", name="valid_entry_type"),
        CheckConstraint("amount_delta_minor <> 0", name="amount_delta_non_zero"),
        CheckConstraint("balance_after_minor >= 0", name="valid_balance_after_minor"),
        Index("ix_gift_card_ledger_entries_gift_card_id", "gift_card_id"),
        Index("ix_gift_card_ledger_entries_source", "source_type", "source_id"),
        Index(
            "uq_gift_card_ledger_entries_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
    )

    gift_card_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gift_cards.id"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(12), nullable=False)
    amount_delta_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("gift_card_ledger_entries.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
