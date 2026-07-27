from datetime import date, time

from sqlalchemy import Boolean, CheckConstraint, Date, Index, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class HolidayCalendar(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """A date-specific override to `BusinessHours` — a full closure or
    special hours for a named day (festival, maintenance closure, seasonal
    schedule). Soft-deletable like `DiningArea`: staff manage this list ahead
    of time and may need to remove an entry added in error, while past
    entries stay queryable for reporting on historical closures.

    When `is_closed` is false, `opens_at`/`closes_at` carry the special
    hours for that date; when true, both are null and the whole day is
    closed regardless of `BusinessHours`.
    """

    __tablename__ = "holiday_calendar"
    __table_args__ = (
        CheckConstraint(
            "is_closed OR (opens_at IS NOT NULL AND closes_at IS NOT NULL)",
            name="valid_special_hours",
        ),
        Index(
            "uq_holiday_calendar_active_date",
            "holiday_date",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    opens_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    closes_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
