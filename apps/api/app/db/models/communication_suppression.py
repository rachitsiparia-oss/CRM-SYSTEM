import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

SUPPRESSION_DESTINATION_TYPES = ("email", "phone")

SUPPRESSION_REASONS = (
    "hard_bounce",
    "spam_complaint",
    "invalid_destination",
    "manual_block",
    "customer_request",
    "unsubscribed",
)

SUPPRESSION_SCOPES = ("all", "promotional_only")


class CommunicationSuppression(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Never physically deleted (this phase's own instruction's privacy/
    retention section: "suppression retention" must survive) — lifting a
    suppression sets `is_active=False`/`lifted_at`/`lifted_by` rather than
    removing the row, and a destination can be re-suppressed later as a new
    active row."""

    __tablename__ = "communication_suppressions"
    __table_args__ = (
        CheckConstraint(
            f"destination_type IN {SUPPRESSION_DESTINATION_TYPES!r}",
            name="valid_destination_type",
        ),
        CheckConstraint(f"reason IN {SUPPRESSION_REASONS!r}", name="valid_reason"),
        CheckConstraint(f"scope IN {SUPPRESSION_SCOPES!r}", name="valid_scope"),
        Index(
            "uq_communication_suppressions_active_destination",
            "destination_type",
            "destination_value",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    destination_type: Mapped[str] = mapped_column(String(16), nullable=False)
    destination_value: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(24), nullable=False, default="all")
    suppressed_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lifted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
