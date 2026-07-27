import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 11.1 / PROJECT_PLAN.md section 11.1's
# documented 14-state list, plus `expired` (this phase's own addition — see
# the module docstring below for why). DATABASE_AND_API.md also documents a
# *second*, separate `approval_status` column carrying a subset of these
# same values (`pending_review`/`needs_clarification`/`approved`/
# `rejected`) — collapsed into this single `status` column instead, since a
# reservation cannot simultaneously disagree with itself about whether it
# is approved; keeping two overlapping status columns risks them drifting
# apart. See DATABASE_AND_API.md section 11.5 for the full reasoning.
RESERVATION_STATUSES = (
    "requested",
    "pending_review",
    "needs_clarification",
    "approved",
    "rejected",
    "confirmation_sending",
    "confirmed",
    "reminder_scheduled",
    "arrived",
    "seated",
    "completed",
    "no_show",
    "cancelled_by_customer",
    "cancelled_by_restaurant",
    "expired",
)

RESERVATION_SOURCES = ("phone", "walk_in", "online", "whatsapp", "staff")

CANCELLATION_SOURCES = ("customer", "restaurant")


class Reservation(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """PROJECT_PLAN.md section 11 / DATABASE_AND_API.md section 11.1.

    No soft-delete: a reservation is never removed, only moved to a
    terminal status (`completed`/`no_show`/`cancelled_by_*`/`expired`) —
    the same choice `Order` already makes, for the same reason (a
    reservation's full history must remain queryable for customer-360
    statistics and reporting).

    Every reservation requires human approval — PROJECT_PLAN.md section
    11.2's explicit rule ("No automated approval is permitted"). A walk-in
    is the one case this phase's own instruction adds that the documented
    approval-gated flow does not anticipate: a guest standing at the host
    stand needs a table now, not a multi-step asynchronous review of a
    future booking. The human-in-the-loop requirement is satisfied by the
    staff member who creates and immediately seats the walk-in being the
    approval itself — `app.reservations.service.create_walk_in` creates the
    row already `approved`/`arrived` with `approved_by` set to the acting
    staff member, never bypassing the rule, just skipping the *asynchronous
    queue* that only applies to a booking that will happen later.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(f"status IN {RESERVATION_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"source IN {RESERVATION_SOURCES!r}", name="valid_source"),
        CheckConstraint(
            f"cancellation_source IS NULL OR cancellation_source IN {CANCELLATION_SOURCES!r}",
            name="valid_cancellation_source",
        ),
        CheckConstraint("party_size > 0", name="valid_party_size"),
        CheckConstraint("end_time IS NULL OR end_time > start_time", name="valid_time_window"),
        CheckConstraint(
            "deposit_amount_minor IS NULL OR deposit_amount_minor >= 0",
            name="valid_deposit_amount_minor",
        ),
        Index("ix_reservations_customer_id", "customer_id"),
        Index("ix_reservations_dining_area_id", "dining_area_id"),
        Index("ix_reservations_status", "status"),
        Index("ix_reservations_date_start_time", "reservation_date", "start_time"),
        Index("ix_reservations_order_id", "order_id"),
        Index("ix_reservations_assigned_staff_id", "assigned_staff_id"),
        Index(
            "uq_reservations_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    reservation_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    guest_name: Mapped[str] = mapped_column(String(180), nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    dining_area_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dining_areas.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="requested")
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    is_walk_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deposit_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deposit_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Creation idempotency (CLAUDE.md section 7: "Prevent duplicate ...
    # reservations ... using ... idempotency") — mirrors Order.idempotency_key.
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
