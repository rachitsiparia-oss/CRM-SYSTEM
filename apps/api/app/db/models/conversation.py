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

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 12.1 sketches only channel/customer_id/
# lead_id/subject/status/assigned_staff_id/last_message_at/unread_count.
# This phase's own instruction requires a materially larger set (priority,
# a fuller status list, first-response/resolution timestamps, snooze,
# guest identity for unmatched senders) — see the Phase 10 deviations
# section for the full accounting.
CONVERSATION_STATUSES = (
    "open",
    "pending",
    "waiting_on_customer",
    "waiting_on_staff",
    "snoozed",
    "resolved",
    "closed",
    "spam",
)

CONVERSATION_PRIORITIES = ("low", "normal", "high", "urgent")

# How the conversation itself came to exist — distinct from a message's own
# `direction` (an inbound message can arrive on a `staff_initiated`
# conversation once staff has already reached out first).
CONVERSATION_SOURCES = ("inbound", "staff_initiated", "system_event")


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Never deleted, never fully re-opened into a different customer —
    only ever moved between the statuses above. `customer_id`/`lead_id` are
    direct pointers (mirrors `Reservation.customer_id`); a broader set of
    entity links (order, reservation, waitlist entry) that can be plural
    over a conversation's life lives in `ConversationLink`, not here.
    """

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(f"status IN {CONVERSATION_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"priority IN {CONVERSATION_PRIORITIES!r}", name="valid_priority"),
        CheckConstraint(f"source IN {CONVERSATION_SOURCES!r}", name="valid_source"),
        CheckConstraint("unread_count >= 0", name="valid_unread_count"),
        Index("ix_conversations_customer_id", "customer_id"),
        Index("ix_conversations_lead_id", "lead_id"),
        Index("ix_conversations_channel_id", "channel_id"),
        Index("ix_conversations_status", "status"),
        Index("ix_conversations_assigned_staff_id", "assigned_staff_id"),
        Index("ix_conversations_last_activity_at", "last_activity_at"),
    )

    conversation_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    # Populated when an inbound sender cannot yet be matched to an existing
    # customer/lead — mirrors `Reservation.guest_name`/`phone_e164`/`email`
    # for the same "we don't have a record yet" case.
    guest_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_outbound_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spam_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
