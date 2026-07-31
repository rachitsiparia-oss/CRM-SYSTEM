import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

SCHEDULED_MESSAGE_PURPOSES = (
    "reservation_reminder",
    "feedback_request",
    "lead_follow_up",
    "manual",
    # Added under the 2026-07-30 Phase 12 scope-expansion decision — a
    # campaign send reuses this same scheduling engine rather than a
    # second one (GROWTH_AND_INTELLIGENCE.md section 3).
    "campaign",
)

# CLAUDE.md section 14, "engine, not scheduler" — no external scheduler
# framework is introduced; `app.communications.scheduling.process_due`
# is the explicit entry point a worker/cron calls, driven entirely by this
# table's `status`/`scheduled_for`/`processing_locked_at` columns.
SCHEDULED_MESSAGE_STATUSES = ("scheduled", "processing", "sent", "cancelled", "failed")


class ScheduledMessage(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    __tablename__ = "scheduled_messages"
    __table_args__ = (
        CheckConstraint(f"purpose IN {SCHEDULED_MESSAGE_PURPOSES!r}", name="valid_purpose"),
        CheckConstraint(f"status IN {SCHEDULED_MESSAGE_STATUSES!r}", name="valid_status"),
        CheckConstraint("attempt_count >= 0", name="valid_attempt_count"),
        Index("ix_scheduled_messages_status_scheduled_for", "status", "scheduled_for"),
        Index(
            "uq_scheduled_messages_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("message_templates.id"), nullable=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=False
    )
    recipient_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), nullable=False, default="Asia/Kolkata")
    # `none_as_null=True` — see the identical note on
    # `TaskRecord.recurrence_rule`.
    template_variables: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="scheduled")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    processing_locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    result_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
