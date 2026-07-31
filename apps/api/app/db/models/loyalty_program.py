import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 5.1: "Loyalty points cannot be
# represented only by an editable balance." draft/active/paused/archived
# mirrors the lifecycle vocabulary every other configurable-entity phase in
# this project uses (knowledge articles, transition templates).
LOYALTY_PROGRAM_STATUSES = ("draft", "active", "paused", "archived")


class LoyaltyProgram(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Program-level configuration — PROJECT_PLAN.md section 12's "RKPR
    Rewards" defaults are seeded as one row here, not hardcoded in code, so
    a future rate change is a data edit, not a deployment.

    Only one row may be `is_default AND status = 'active'` at a time,
    enforced by the partial unique index below (this phase's own rule:
    "Only one default active program should exist").
    """

    __tablename__ = "loyalty_programs"
    __table_args__ = (
        CheckConstraint(f"status IN {LOYALTY_PROGRAM_STATUSES!r}", name="valid_status"),
        CheckConstraint("points_per_currency_unit > 0", name="valid_points_per_currency_unit"),
        CheckConstraint("currency_unit_minor > 0", name="valid_currency_unit_minor"),
        CheckConstraint("redemption_points_per_unit > 0", name="valid_redemption_points_per_unit"),
        CheckConstraint("redemption_value_minor > 0", name="valid_redemption_value_minor"),
        CheckConstraint("minimum_redemption_points >= 0", name="valid_minimum_redemption_points"),
        CheckConstraint(
            "max_redemption_percent IS NULL "
            "OR (max_redemption_percent > 0 AND max_redemption_percent <= 100)",
            name="valid_max_redemption_percent",
        ),
        CheckConstraint(
            "points_expiry_days IS NULL OR points_expiry_days > 0",
            name="valid_points_expiry_days",
        ),
        Index(
            "uq_loyalty_programs_one_default_active",
            "is_default",
            unique=True,
            postgresql_where=text("is_default AND status = 'active'"),
        ),
        Index("ix_loyalty_programs_status", "status"),
    )

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    points_display_name: Mapped[str] = mapped_column(String(60), nullable=False, default="points")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Earning: floor(eligible_spend_minor / currency_unit_minor) *
    # points_per_currency_unit. PROJECT_PLAN.md default: 1 point per ₹10.
    points_per_currency_unit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    currency_unit_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    # Redemption: redemption_value_minor per redemption_points_per_unit.
    # PROJECT_PLAN.md default: 100 points = ₹25.
    redemption_points_per_unit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    redemption_value_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=2500)
    minimum_redemption_points: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    max_redemption_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    points_expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True, default=365)
    terms_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# GROWTH_AND_INTELLIGENCE.md section 5.8. Rank is a plain integer, not tied
# to any hardcoded name — "Example tier codes may be configured, but no
# tier threshold is authoritative until approved in configuration."
TIER_QUALIFICATION_METRICS = (
    "lifetime_spend",
    "rolling_spend",
    "points_earned",
    "completed_orders",
    "visits",
    "manual",
)


class LoyaltyTier(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    __tablename__ = "loyalty_tiers"
    __table_args__ = (
        CheckConstraint(
            f"qualification_metric IN {TIER_QUALIFICATION_METRICS!r}",
            name="valid_qualification_metric",
        ),
        CheckConstraint("rank >= 0", name="valid_rank"),
        CheckConstraint("threshold >= 0", name="valid_threshold"),
        CheckConstraint(
            "rolling_window_days IS NULL OR rolling_window_days > 0",
            name="valid_rolling_window_days",
        ),
        CheckConstraint("points_multiplier > 0", name="valid_points_multiplier"),
        Index(
            "uq_loyalty_tiers_program_code",
            "program_id",
            "code",
            unique=True,
        ),
        Index("ix_loyalty_tiers_program_rank", "program_id", "rank"),
    )

    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_programs.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    qualification_metric: Mapped[str] = mapped_column(String(24), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal(0))
    rolling_window_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    benefits_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    points_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.00")
    )
    review_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    downgrade_grace_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    icon: Mapped[str | None] = mapped_column(String(60), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
