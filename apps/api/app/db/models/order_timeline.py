import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

# This phase's own instruction: "Automatically record: Created, Assigned,
# Status changed, Payment updated, Note added, Cancelled, Completed, Manual
# edits."
ORDER_TIMELINE_EVENT_TYPES = (
    "created",
    "assigned",
    "status_changed",
    "payment_updated",
    "note_added",
    "cancelled",
    "completed",
    "manual_edit",
)


class OrderTimeline(UUIDPrimaryKeyMixin, Base):
    """This phase's own instruction: "Every timeline entry: Timestamp,
    Staff, Action, Metadata." Mirrors LeadActivity's shape — the broader
    activity feed, distinct from the status-only OrderStatusHistory ledger.
    """

    __tablename__ = "order_timeline"
    __table_args__ = (
        CheckConstraint(f"event_type IN {ORDER_TIMELINE_EVENT_TYPES!r}", name="valid_event_type"),
        Index("ix_order_timeline_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
