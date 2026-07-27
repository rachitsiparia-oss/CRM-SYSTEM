from datetime import time

from sqlalchemy import Boolean, CheckConstraint, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


class BusinessHours(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """One row per day of week — PROJECT_PLAN.md section 3.3's documented
    operating hours (seeded in task #111). Exactly seven rows exist at all
    times; staff edit them, nothing ever deletes one, so there is no
    soft-delete mixin here — the same "always-present reference rows" shape
    this phase's own instruction implies for a weekly schedule.

    `day_of_week` follows Python's `date.weekday()` convention (0=Monday,
    6=Sunday) so the availability engine can index straight off
    `reservation_date.weekday()` without a lookup table.

    `closes_next_day` covers Friday/Saturday closing at 12:00 AM — the
    closing time is on the calendar day *after* `day_of_week`, not a
    same-day close-before-open error.
    """

    __tablename__ = "business_hours"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="valid_day_of_week"),
        CheckConstraint(
            "is_closed OR (opens_at IS NOT NULL AND closes_at IS NOT NULL)",
            name="valid_open_hours",
        ),
        CheckConstraint(
            "(break_starts_at IS NULL) = (break_ends_at IS NULL)", name="valid_break_window"
        ),
    )

    day_of_week: Mapped[int] = mapped_column(unique=True, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opens_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    closes_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    closes_next_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    break_starts_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_ends_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
