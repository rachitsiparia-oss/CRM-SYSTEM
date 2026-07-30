import uuid
from datetime import date, time

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

AVAILABILITY_TYPES = ("available", "unavailable", "preferred")


class StaffAvailabilityWindow(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """This phase's own instruction section 27 — lightweight roster-input
    availability, either recurring (`day_of_week`) or date-specific
    (`specific_date`). No automatic roster optimization is implemented or
    promised; this is input data only, consumed by staff when building a
    roster manually."""

    __tablename__ = "staff_availability_windows"
    __table_args__ = (
        CheckConstraint(f"availability_type IN {AVAILABILITY_TYPES!r}", name="valid_type"),
        CheckConstraint(
            "day_of_week IS NOT NULL OR specific_date IS NOT NULL", name="valid_recurrence_target"
        ),
        CheckConstraint(
            "day_of_week IS NULL OR day_of_week BETWEEN 0 AND 6", name="valid_day_of_week"
        ),
        Index("ix_staff_availability_windows_staff_user_id", "staff_user_id"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    availability_type: Mapped[str] = mapped_column(String(16), nullable=False)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    specific_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
