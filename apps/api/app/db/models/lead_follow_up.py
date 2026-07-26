import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# CORE_CRM_MODULES.md section 5.10.
FOLLOW_UP_STATUSES = ("scheduled", "due", "completed", "cancelled", "missed")


class LeadFollowUp(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """DATABASE_AND_API.md section 7.4."""

    __tablename__ = "lead_follow_ups"
    __table_args__ = (
        CheckConstraint(f"status IN {FOLLOW_UP_STATUSES!r}", name="valid_status"),
        Index("ix_lead_follow_ups_lead_id", "lead_id"),
        Index("ix_lead_follow_ups_assigned_to_scheduled_at", "assigned_to", "scheduled_at"),
        Index(
            "ix_lead_follow_ups_overdue",
            "scheduled_at",
            postgresql_where=text("status IN ('scheduled', 'due')"),
        ),
    )

    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), nullable=False)
    assigned_to: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Extensions beyond the documented column list, needed for
    # CORE_CRM_MODULES.md section 5.10's "purpose" and "channel" fields.
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
