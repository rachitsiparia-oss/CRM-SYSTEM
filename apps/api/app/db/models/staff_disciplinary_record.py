import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

SEVERITIES = ("minor", "moderate", "severe")
DISCIPLINARY_STATUSES = ("open", "resolved", "appealed")


class StaffDisciplinaryRecord(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """PROJECT_PLAN.md section "Scope — Staff & HR": "Disciplinary records
    with strict permissions." Gated by the dedicated
    `staff.disciplinary.view`/`.manage` permissions (not the broader
    `staff.hr_sensitive.read`) and never surfaced in the general staff
    directory — this phase's own instruction section 26."""

    __tablename__ = "staff_disciplinary_records"
    __table_args__ = (
        CheckConstraint(f"severity IN {SEVERITIES!r}", name="valid_severity"),
        CheckConstraint(f"status IN {DISCIPLINARY_STATUSES!r}", name="valid_status"),
        Index("ix_staff_disciplinary_records_staff_user_id", "staff_user_id"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
