import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

ATTENDANCE_STATUSES = (
    "present",
    "absent",
    "late",
    "half_day",
    "on_leave",
    "weekly_off",
    "holiday",
    "missed_punch",
)
ATTENDANCE_SOURCES = ("manual", "roster_derived")
APPROVAL_STATES = ("pending", "approved", "rejected")


class AttendanceRecord(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """This phase's own instruction section 19 — manual/roster-derived
    attendance, no biometric hardware integration. Each correction is
    additionally recorded as its own immutable `AttendanceCorrection` row
    (`is_corrected`/`correction_reason`/`corrected_by` here only reflect
    the record's current state, matching the "current state + append-only
    history" pattern every other Phase 11 history pair uses)."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        CheckConstraint(f"status IN {ATTENDANCE_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"source IN {ATTENDANCE_SOURCES!r}", name="valid_source"),
        CheckConstraint(f"approval_state IN {APPROVAL_STATES!r}", name="valid_approval_state"),
        CheckConstraint(
            "actual_check_out_at IS NULL OR actual_check_in_at IS NULL "
            "OR actual_check_out_at >= actual_check_in_at",
            name="valid_checkout_after_checkin",
        ),
        UniqueConstraint("staff_user_id", "attendance_date", name="uq_attendance_records"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_shifts.id"), nullable=True)
    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_check_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_check_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    late_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    early_leave_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worked_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    break_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    is_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approval_state: Mapped[str] = mapped_column(String(16), nullable=False, default="approved")
