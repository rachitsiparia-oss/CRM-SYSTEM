from sqlalchemy import Boolean, CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReservationSettings(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Global, single-row operational configuration — distinct from
    `ReservationPolicies`: that table holds numeric business-rule
    thresholds (deposits, notice windows, buffers, party-size limits);
    this one holds feature toggles and timing config for the engines
    built later in this phase (assignment, waitlist, expiry). Same
    constant-unique-column singleton guard as `ReservationPolicies`.

    Deliberately excludes an "auto-approve online bookings" toggle:
    PROJECT_PLAN.md section 11.2's "No automated approval is permitted"
    is a hard business rule, not a configurable preference, and making it
    a toggle here would let it be silently switched off — CLAUDE.md
    section 24 forbids exactly that kind of shortcut.
    """

    __tablename__ = "reservation_settings"
    __table_args__ = (
        CheckConstraint("singleton_guard", name="valid_singleton_guard"),
        CheckConstraint(
            "default_reservation_duration_minutes > 0",
            name="valid_default_reservation_duration_minutes",
        ),
        CheckConstraint(
            "pending_request_expiry_minutes IS NULL OR pending_request_expiry_minutes > 0",
            name="valid_pending_request_expiry_minutes",
        ),
        CheckConstraint(
            "reminder_lead_time_minutes IS NULL OR reminder_lead_time_minutes > 0",
            name="valid_reminder_lead_time_minutes",
        ),
    )

    singleton_guard: Mapped[bool] = mapped_column(
        Boolean, unique=True, nullable=False, default=True
    )
    default_reservation_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90
    )
    auto_assignment_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    waitlist_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    online_booking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    walk_in_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pending_request_expiry_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_lead_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
