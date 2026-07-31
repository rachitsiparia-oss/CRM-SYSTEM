from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 7.2 — added 2026-07-30.
REFERRAL_PROGRAM_STATUSES = ("draft", "active", "paused", "archived")


class ReferralProgram(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Rewards post through the Loyalty ledger (`referral_reward` entry
    type) or the internal-credit ledger — never an untracked balance
    (GROWTH_AND_INTELLIGENCE.md section 7.1). `reward_ledger` selects
    which.
    """

    __tablename__ = "referral_programs"
    __table_args__ = (
        CheckConstraint(f"status IN {REFERRAL_PROGRAM_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "reward_ledger IN ('loyalty_points', 'internal_credit')", name="valid_reward_ledger"
        ),
        CheckConstraint("referrer_reward_amount > 0", name="valid_referrer_reward_amount"),
        CheckConstraint("referee_reward_amount > 0", name="valid_referee_reward_amount"),
        CheckConstraint(
            "qualifying_order_minimum_minor IS NULL OR qualifying_order_minimum_minor >= 0",
            name="valid_qualifying_order_minimum_minor",
        ),
        CheckConstraint("reward_hold_days >= 0", name="valid_reward_hold_days"),
        Index("ix_referral_programs_status", "status"),
    )

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    referrer_eligibility_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    referee_eligibility_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualifying_order_minimum_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reward_ledger: Mapped[str] = mapped_column(String(16), nullable=False, default="loyalty_points")
    referrer_reward_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    referee_reward_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    max_active_codes_per_referrer: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_rewarded_referrals_per_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    window_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reward_hold_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
