import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

PROCESSING_STATUSES = ("received", "processed", "ignored", "failed")

# This phase's own instruction section 16's normalized delivery-status
# vocabulary — distinct from `Message.delivery_status` (the CRM's own
# canonical lifecycle) because a provider's status webhook uses its own
# vendor-specific vocabulary that must be normalized *before* it is ever
# allowed to move `Message.delivery_status` forward.
NORMALIZED_STATUSES = (
    "accepted",
    "queued",
    "sent",
    "delivered",
    "read",
    "failed",
    "rejected",
    "undeliverable",
)


class ProviderStatusEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Idempotency ledger for provider delivery/status webhooks — kept
    separate from `InboundWebhookEvent` because inbound messages and
    delivery-status callbacks are different provider endpoints with
    different payload semantics (this phase's own instruction treats them
    as two distinct sections, 15 and 16)."""

    __tablename__ = "provider_status_events"
    __table_args__ = (
        CheckConstraint(f"processing_status IN {PROCESSING_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            f"normalized_status IN {NORMALIZED_STATUSES!r}", name="valid_normalized_status"
        ),
        UniqueConstraint("provider", "provider_event_id", name="uq_provider_status_events_event"),
        Index("ix_provider_status_events_message_id", "message_id"),
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=True
    )
    provider_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    normalized_status: Mapped[str] = mapped_column(String(24), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(16), nullable=False, default="received")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
