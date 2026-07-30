import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

MESSAGE_DIRECTIONS = ("inbound", "outbound", "internal")

MESSAGE_TYPES = (
    "text",
    "email",
    "sms",
    "whatsapp",
    "system_event",
    "template",
    "internal_note",
    "attachment",
    "reservation_update",
    "order_update",
    "feedback_request",
)

# One column carries both lifecycles this phase's own instruction describes
# separately (outbound: draft/queued/processing/sent/delivered/read/failed/
# cancelled/suppressed; inbound: received/processed/assigned/replied/
# resolved) — the same collapse `Reservation.status` made of its own two
# documented columns. Which subset is valid for a given row is enforced by
# `app.communications.states`, keyed on `direction`, not by a second column.
OUTBOUND_MESSAGE_STATUSES = (
    "draft",
    "queued",
    "processing",
    "sent",
    "delivered",
    "read",
    "failed",
    "cancelled",
    "suppressed",
)
INBOUND_MESSAGE_STATUSES = ("received", "processed", "assigned", "replied", "resolved", "spam")
INTERNAL_MESSAGE_STATUSES = ("created",)
ALL_MESSAGE_STATUSES = (
    OUTBOUND_MESSAGE_STATUSES + INBOUND_MESSAGE_STATUSES + INTERNAL_MESSAGE_STATUSES
)


class Message(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """DATABASE_AND_API.md section 12.2, extended per this phase's own
    instruction (reply-to threading, idempotency key, rendered template
    variables, retry count, and the read/delivered/sent ordering
    constraints below). Never deleted or overwritten in place — a
    correction is a new message referencing the old one via `reply_to_
    message_id`, not an edit."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(f"direction IN {MESSAGE_DIRECTIONS!r}", name="valid_direction"),
        CheckConstraint(f"message_type IN {MESSAGE_TYPES!r}", name="valid_message_type"),
        CheckConstraint(
            f"delivery_status IN {ALL_MESSAGE_STATUSES!r}", name="valid_delivery_status"
        ),
        CheckConstraint(
            "direction != 'outbound' OR recipient_reference IS NOT NULL",
            name="outbound_requires_recipient",
        ),
        CheckConstraint(
            "message_type != 'internal_note' OR recipient_reference IS NULL",
            name="internal_note_has_no_recipient",
        ),
        CheckConstraint(
            "delivered_at IS NULL OR sent_at IS NULL OR delivered_at >= sent_at",
            name="delivered_after_sent",
        ),
        CheckConstraint(
            "read_at IS NULL OR delivered_at IS NULL OR read_at >= delivered_at",
            name="read_after_delivered",
        ),
        CheckConstraint("retry_count >= 0", name="valid_retry_count"),
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_delivery_status", "delivery_status"),
        Index("ix_messages_created_at", "created_at"),
        Index(
            "uq_messages_provider_message_id",
            "channel_id",
            "provider_message_id",
            unique=True,
            postgresql_where=text("provider_message_id IS NOT NULL"),
        ),
        Index(
            "uq_messages_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sender_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("message_templates.id"), nullable=True
    )
    # `none_as_null=True` — see the identical note on
    # `TaskRecord.recurrence_rule`; without it, a Python `None` here would
    # store a JSONB `null` literal rather than a true SQL NULL.
    rendered_template_variables: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reply_to_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
