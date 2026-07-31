import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 5.2.
LOYALTY_ACCOUNT_STATUSES = ("active", "suspended", "closed", "merged")


class LoyaltyAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One account per customer per program. Balances are a projection —
    `app.loyalty.ledger` is the only module permitted to write them, always
    inside the same transaction as the `LoyaltyLedgerEntry` row that
    justifies the change, mirroring `StockBalance`'s relationship to
    `stock_movements` (DATABASE_AND_API.md section 9.3)."""

    __tablename__ = "loyalty_accounts"
    __table_args__ = (
        CheckConstraint(f"status IN {LOYALTY_ACCOUNT_STATUSES!r}", name="valid_status"),
        CheckConstraint("points_balance >= 0", name="valid_points_balance"),
        CheckConstraint("lifetime_points_earned >= 0", name="valid_lifetime_earned"),
        CheckConstraint("lifetime_points_redeemed >= 0", name="valid_lifetime_redeemed"),
        CheckConstraint("lifetime_points_expired >= 0", name="valid_lifetime_expired"),
        Index("uq_loyalty_accounts_customer_program", "customer_id", "program_id", unique=True),
        Index("ix_loyalty_accounts_program_id", "program_id"),
        Index("ix_loyalty_accounts_current_tier_id", "current_tier_id"),
    )

    account_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_programs.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    points_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_points_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_points_redeemed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_points_expired: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_tier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("loyalty_tiers.id"), nullable=True
    )
    tier_effective_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tier_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enrollment_source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    terms_version_accepted: Mapped[str | None] = mapped_column(String(30), nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


# GROWTH_AND_INTELLIGENCE.md section 5.8: "Tier changes create history
# records" — never overwritten, per this phase's own instruction.
TIER_MEMBERSHIP_SOURCES = ("automatic", "manual", "imported", "migration")


class LoyaltyTierMembership(UUIDPrimaryKeyMixin, Base):
    """Append-only tier history. `effective_to IS NULL` marks the current
    row for an account; a tier change closes the current row
    (`effective_to = now()`) and inserts a new one rather than mutating it.
    """

    __tablename__ = "loyalty_tier_memberships"
    __table_args__ = (
        CheckConstraint(f"source IN {TIER_MEMBERSHIP_SOURCES!r}", name="valid_source"),
        Index("ix_loyalty_tier_memberships_account_id", "account_id"),
        Index(
            "uq_loyalty_tier_memberships_one_current",
            "account_id",
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
        ),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_accounts.id"), nullable=False)
    tier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_tiers.id"), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qualification_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
