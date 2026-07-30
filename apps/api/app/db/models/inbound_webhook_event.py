import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

PROCESSING_STATUSES = ("received", "processed", "failed", "ignored")


class InboundWebhookEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Idempotency ledger for provider inbound-message webhooks — the
    unique `(provider, provider_event_id)` constraint is the DB-level
    enforcement of CLAUDE.md section 7's "unique provider event IDs", so a
    provider's at-least-once retry of the same webhook is a no-op past the
    first insert. `raw_payload` is retained for reprocessing/debugging;
    callers must redact secrets before writing it (CLAUDE.md section 19,
    "no full sensitive webhook payload dumps in normal logs" — same rule
    applied to storage, not just logs)."""

    __tablename__ = "inbound_webhook_events"
    __table_args__ = (
        CheckConstraint(f"processing_status IN {PROCESSING_STATUSES!r}", name="valid_status"),
        UniqueConstraint("provider", "provider_event_id", name="uq_inbound_webhook_events_event"),
        Index("ix_inbound_webhook_events_channel_id", "channel_id"),
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=True
    )
    provider_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(16), nullable=False, default="received")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    resulting_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True
    )
