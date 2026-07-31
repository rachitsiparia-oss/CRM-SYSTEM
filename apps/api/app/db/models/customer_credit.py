import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 10 — added 2026-07-30. Non-
# withdrawable, non-transferable, no customer top-up (section 10.2).
CUSTOMER_CREDIT_ACCOUNT_STATUSES = ("active", "suspended", "closed")


class CustomerCreditAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One account per customer. Distinct from `LoyaltyAccount` — this is
    money-denominated store credit (service recovery, approved refund as
    credit, campaign/referral reward, goodwill), not points
    (GROWTH_AND_INTELLIGENCE.md section 10.1)."""

    __tablename__ = "customer_credit_accounts"
    __table_args__ = (
        CheckConstraint(f"status IN {CUSTOMER_CREDIT_ACCOUNT_STATUSES!r}", name="valid_status"),
        CheckConstraint("current_balance_minor >= 0", name="valid_current_balance_minor"),
        Index("uq_customer_credit_accounts_customer_id", "customer_id", unique=True),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="active")
    current_balance_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


CUSTOMER_CREDIT_LEDGER_ENTRY_TYPES = ("issue", "redeem", "reverse", "adjust", "expire", "migration")

# GROWTH_AND_INTELLIGENCE.md section 10.4's issuance reasons — recorded on
# `issue_reason` rather than as separate entry types, since the ledger
# mechanics (append-only, signed, reversible) are identical across all of
# them; only the business reason differs.
CUSTOMER_CREDIT_ISSUE_REASONS = (
    "service_recovery",
    "refund_as_credit",
    "campaign_reward",
    "referral_reward",
    "achievement_reward",
    "goodwill_adjustment",
    "migration",
)


class CustomerCreditLedgerEntry(UUIDPrimaryKeyMixin, Base):
    """Append-only — same shape as `GiftCardLedgerEntry`/
    `LoyaltyLedgerEntry`. `app.customer_credit.ledger` is the only writer.
    No code path here ever produces a cash payout, transfer, or top-up —
    there is no entry type for any of those (GROWTH_AND_INTELLIGENCE.md
    section 10.2)."""

    __tablename__ = "customer_credit_ledger_entries"
    __table_args__ = (
        CheckConstraint(
            f"entry_type IN {CUSTOMER_CREDIT_LEDGER_ENTRY_TYPES!r}", name="valid_entry_type"
        ),
        CheckConstraint(
            f"issue_reason IS NULL OR issue_reason IN {CUSTOMER_CREDIT_ISSUE_REASONS!r}",
            name="valid_issue_reason",
        ),
        CheckConstraint("amount_delta_minor <> 0", name="amount_delta_non_zero"),
        CheckConstraint("balance_after_minor >= 0", name="valid_balance_after_minor"),
        Index("ix_customer_credit_ledger_entries_account_id", "account_id"),
        Index("ix_customer_credit_ledger_entries_source", "source_type", "source_id"),
        Index(
            "uq_customer_credit_ledger_entries_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_credit_accounts.id"), nullable=False
    )
    entry_type: Mapped[str] = mapped_column(String(12), nullable=False)
    issue_reason: Mapped[str | None] = mapped_column(String(24), nullable=True)
    amount_delta_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_credit_ledger_entries.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
