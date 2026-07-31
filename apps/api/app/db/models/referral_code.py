import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Normalized (uppercased) and unique — GROWTH_AND_INTELLIGENCE.md
    section 7.3. A referrer may hold more than one active code only up to
    `ReferralProgram.max_active_codes_per_referrer`, enforced in
    `app.referrals.service`, not by schema (the limit is per-program
    configuration, not a fixed constant).
    """

    __tablename__ = "referral_codes"
    __table_args__ = (
        Index("uq_referral_codes_code", "code", unique=True),
        Index("ix_referral_codes_program_id", "program_id"),
        Index("ix_referral_codes_referrer_customer_id", "referrer_customer_id"),
    )

    code: Mapped[str] = mapped_column(String(30), nullable=False)
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("referral_programs.id"), nullable=False
    )
    referrer_customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
