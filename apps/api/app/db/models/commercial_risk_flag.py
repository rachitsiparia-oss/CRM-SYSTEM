import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# This phase's own "lightweight, auditable controls" list: repeated manual
# adjustments, repeated reversals, excessive coupon failures, high-value
# issuance, self-referral/identity-overlap, duplicate/idempotency conflicts.
COMMERCIAL_RISK_FLAG_TYPES = (
    "repeated_manual_adjustment",
    "repeated_reversal",
    "excessive_coupon_failures",
    "high_value_issuance",
    "self_referral_attempt",
    "identity_overlap",
    "duplicate_attempt",
)
COMMERCIAL_RISK_FLAG_STATUSES = ("open", "reviewing", "resolved", "dismissed")


class CommercialRiskFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A review queue, not an enterprise fraud platform — this phase's own
    scope boundary. `related_type`/`related_id` point at the record under
    review (a redemption, ledger entry, referral relationship, etc.),
    mirroring the polymorphic-reference pattern `TaskRecord.related_type`
    already established in Phase 10.
    """

    __tablename__ = "commercial_risk_flags"
    __table_args__ = (
        CheckConstraint(f"flag_type IN {COMMERCIAL_RISK_FLAG_TYPES!r}", name="valid_flag_type"),
        CheckConstraint(f"status IN {COMMERCIAL_RISK_FLAG_STATUSES!r}", name="valid_status"),
        Index("ix_commercial_risk_flags_status", "status"),
        Index("ix_commercial_risk_flags_flag_type", "flag_type"),
        Index("ix_commercial_risk_flags_customer_id", "customer_id"),
        Index("ix_commercial_risk_flags_related", "related_type", "related_id"),
    )

    flag_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="open")
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    related_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    related_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("task_records.id"), nullable=True)
