import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

SHIFT_STATUSES = ("scheduled", "published", "completed", "cancelled", "no_show")


class StaffShift(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A roster instance — this phase's own instruction section 17.
    `start_at`/`end_at` are full timestamps (not template time-of-day
    references) so overnight shifts and one-off overrides are handled
    uniformly; overlap detection (`app.staff_operations.shifts`) compares
    these ranges directly rather than reasoning about time-of-day wraparound.
    Publishing does not mutate history — `AuditedMixin.version` protects
    concurrent edits, and every status change is a fresh
    `StaffShiftChangeRequest` or a direct field update, never a silent
    overwrite of a already-published shift without the version check."""

    __tablename__ = "staff_shifts"
    __table_args__ = (
        CheckConstraint(f"status IN {SHIFT_STATUSES!r}", name="valid_status"),
        CheckConstraint("end_at > start_at", name="valid_end_after_start"),
        Index("ix_staff_shifts_staff_user_id", "staff_user_id"),
        Index("ix_staff_shifts_shift_date", "shift_date"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shift_templates.id"), nullable=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    role_on_shift: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
