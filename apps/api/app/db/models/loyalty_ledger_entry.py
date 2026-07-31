import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 5.4's canonical entry-type list, plus
# `referral_reward` and `achievement_reward` — added under the same
# 2026-07-30 scope-expansion decision that added the Referral and
# Achievement modules themselves (ROADMAP.md Phase 12 completion notes).
LOYALTY_LEDGER_ENTRY_TYPES = (
    "earn_order",
    "earn_campaign",
    "earn_manual",
    "redeem_order",
    "redeem_reward",
    "expire",
    "reverse_earn",
    "reverse_redemption",
    "service_recovery_credit",
    "merge_transfer",
    "correction",
    "referral_reward",
    "achievement_reward",
)

EARN_ENTRY_TYPES = (
    "earn_order",
    "earn_campaign",
    "earn_manual",
    "service_recovery_credit",
    "referral_reward",
    "achievement_reward",
)
REDEEM_ENTRY_TYPES = ("redeem_order", "redeem_reward")


class LoyaltyLedgerEntry(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """The append-only points ledger — GROWTH_AND_INTELLIGENCE.md section
    5.4: "Every balance change creates an immutable ledger entry... Ledger
    rows are never edited to change history. Corrections use compensating
    entries." Mirrors `StockMovement`'s shape and guarantees exactly
    (DATABASE_AND_API.md section 9.3): signed delta, idempotency key with a
    partial unique index, reversal linkage, `app.loyalty.ledger` is the only
    writer.
    """

    __tablename__ = "loyalty_ledger_entries"
    __table_args__ = (
        CheckConstraint(f"entry_type IN {LOYALTY_LEDGER_ENTRY_TYPES!r}", name="valid_entry_type"),
        CheckConstraint("points_delta <> 0", name="points_delta_non_zero"),
        CheckConstraint("balance_after >= 0", name="valid_balance_after"),
        Index("ix_loyalty_ledger_entries_account_id", "account_id"),
        Index("ix_loyalty_ledger_entries_account_created", "account_id", "created_at"),
        Index("ix_loyalty_ledger_entries_entry_type", "entry_type"),
        Index("ix_loyalty_ledger_entries_source", "source_type", "source_id"),
        Index("ix_loyalty_ledger_entries_expiry_at", "expiry_at"),
        Index("ix_loyalty_ledger_entries_reversal_of_id", "reversal_of_id"),
        Index(
            "uq_loyalty_ledger_entries_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_accounts.id"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(24), nullable=False)
    points_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Non-null only for an earn entry that still has unexpired/unredeemed
    # points outstanding — the FIFO expiry-lot allocation target for
    # `expire`/`redeem_*` entries drawing against it. Prevents double
    # expiry/redemption of the same earned lot (this phase's own rule).
    remaining_in_lot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approval_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("loyalty_ledger_entries.id"), nullable=True
    )
    reversed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("loyalty_ledger_entries.id"), nullable=True
    )
    entry_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
