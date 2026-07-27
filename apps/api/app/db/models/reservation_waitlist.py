import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# This phase's own instruction: "priority, arrival time, party size,
# estimated wait, notification-ready, manual/automatic promotion, reason,
# history." `expired` covers an entry that outlived its own estimated wait
# without being promoted or cancelled — surfaced to staff rather than
# silently dropped.
WAITLIST_STATUSES = ("waiting", "notified", "promoted", "cancelled", "expired")


class ReservationWaitlist(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Walk-in / no-availability waitlist entry. Not soft-deletable: an
    entry is either still open (`waiting`/`notified`) or has reached a
    terminal status (`promoted`/`cancelled`/`expired`) — the same
    "closed, not deleted" treatment `TableBlock` gives a finished
    operational record, so wait-time analytics can query the full history.
    """

    __tablename__ = "reservation_waitlist"
    __table_args__ = (
        CheckConstraint(f"status IN {WAITLIST_STATUSES!r}", name="valid_status"),
        CheckConstraint("party_size > 0", name="valid_party_size"),
        Index("ix_reservation_waitlist_status", "status"),
        Index("ix_reservation_waitlist_customer_id", "customer_id"),
        Index("ix_reservation_waitlist_dining_area_id", "dining_area_id"),
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    guest_name: Mapped[str] = mapped_column(String(180), nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    dining_area_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dining_areas.id"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="waiting")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    estimated_wait_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
