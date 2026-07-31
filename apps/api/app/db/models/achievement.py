import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 8.2 — added 2026-07-30.
ACHIEVEMENT_REWARD_LEDGERS = ("none", "loyalty_points", "internal_credit")


class Achievement(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """`condition` uses the same constrained rule schema as offers/segments
    (`app.commercial_rules`) — no bespoke scripting layer."""

    __tablename__ = "achievements"
    __table_args__ = (
        CheckConstraint(
            f"reward_ledger IN {ACHIEVEMENT_REWARD_LEDGERS!r}", name="valid_reward_ledger"
        ),
        CheckConstraint(
            "reward_ledger = 'none' OR reward_amount > 0", name="reward_amount_when_rewarding"
        ),
        CheckConstraint("cooldown_days IS NULL OR cooldown_days > 0", name="valid_cooldown_days"),
        Index("ix_achievements_is_active", "is_active"),
    )

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(60), nullable=True)
    condition_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Constrained condition tree, validated against app.commercial_rules.
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reward_ledger: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    reward_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_repeatable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cooldown_days: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CustomerAchievementAward(UUIDPrimaryKeyMixin, Base):
    """Immutable and idempotent — GROWTH_AND_INTELLIGENCE.md section 8.3.
    `source_event_key` is the idempotency anchor: the same triggering event
    can never produce two awards (partial unique index below)."""

    __tablename__ = "customer_achievement_awards"
    __table_args__ = (
        Index("ix_customer_achievement_awards_customer_id", "customer_id"),
        Index("ix_customer_achievement_awards_achievement_id", "achievement_id"),
        Index(
            "uq_customer_achievement_awards_source_event",
            "achievement_id",
            "customer_id",
            "source_event_key",
            unique=True,
        ),
        # A non-repeatable achievement can only ever be awarded once per
        # customer, enforced structurally rather than trusted to service code.
        Index(
            "uq_customer_achievement_awards_non_repeatable",
            "achievement_id",
            "customer_id",
            unique=True,
            postgresql_where=text("is_repeatable_award = false"),
        ),
    )

    achievement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("achievements.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    source_event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    # Snapshot of Achievement.is_repeatable at award time, so the partial
    # unique index above stays correct even if the definition changes later.
    is_repeatable_award: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reward_ledger_entry_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
