import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

# This phase's own instruction: "Every action must be logged: Created,
# Edited, Confirmed, Assigned, Checked In, Moved, Cancelled, Completed, No
# Show." `waitlisted`/`promoted` are this phase's own additions, covering the
# waitlist-to-reservation promotion flow the instruction also names, which
# the base list above does not otherwise capture. `status_changed` is the
# same non-exhaustive-list catch-all `OrderTimeline` uses: the instruction's
# own list does not individually name every one of the 15 statuses (there is
# no "Approved"/"Rejected"/"Seated" entry), so any transition not
# individually named above (pending_review, needs_clarification, approved,
# rejected, seated, reminder_scheduled, expired) is recorded as
# `status_changed` rather than inventing an event type per status.
RESERVATION_TIMELINE_EVENT_TYPES = (
    "created",
    "edited",
    "confirmed",
    "assigned",
    "checked_in",
    "moved",
    "cancelled",
    "completed",
    "no_show",
    "waitlisted",
    "promoted",
    "status_changed",
)


class ReservationTimeline(UUIDPrimaryKeyMixin, Base):
    """Broader activity feed for a reservation — mirrors `OrderTimeline`'s
    shape exactly. Distinct from `ReservationStatusHistory` (status-only
    ledger); every status change is dual-written to both, the same pattern
    Orders already established.
    """

    __tablename__ = "reservation_timeline"
    __table_args__ = (
        CheckConstraint(
            f"event_type IN {RESERVATION_TIMELINE_EVENT_TYPES!r}", name="valid_event_type"
        ),
        Index("ix_reservation_timeline_reservation_id", "reservation_id"),
    )

    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservations.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
