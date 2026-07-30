import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

LEAVE_STATUSES = ("draft", "submitted", "approved", "rejected", "cancelled", "withdrawn")
PARTIAL_DAY_PORTIONS = ("first_half", "second_half")


class LeaveRequest(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """This phase's own instruction section 20. Overlap with an already
    approved leave and the staff member's shift schedule is checked in
    `app.staff_operations.leave` (needs a live query over `StaffShift` and
    other `LeaveRequest` rows, not expressible as a single CHECK
    constraint)."""

    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint(f"status IN {LEAVE_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            f"partial_day_portion IS NULL OR partial_day_portion IN {PARTIAL_DAY_PORTIONS!r}",
            name="valid_partial_day_portion",
        ),
        CheckConstraint("end_date >= start_date", name="valid_end_after_start"),
        Index("ix_leave_requests_staff_user_id", "staff_user_id"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    leave_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_partial_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    partial_day_portion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attachment_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
