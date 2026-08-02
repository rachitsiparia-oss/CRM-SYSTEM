import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

# INTEGRATIONS_AUTOMATIONS_REALTIME.md section 17.1. "in_app" never gets a
# row here — the Notification row's own existence (plus read_at/
# dismissed_at/actioned_at) already is the in-app delivery record; a
# second row would just duplicate it. Push is listed as future-ready per
# this phase's own instruction, has no provider adapter yet, and is
# accepted here (constraint-wise) so the channel column doesn't need a
# migration when one is added.
NOTIFICATION_DELIVERY_CHANNELS = ("email", "whatsapp", "sms", "push")
NOTIFICATION_DELIVERY_STATUSES = ("pending", "sent", "delivered", "failed", "skipped")


class NotificationDeliveryAttempt(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """One row per non-in-app delivery attempt for a `Notification` — the
    same "append a new row per attempt" pattern `MessageDeliveryAttempt`
    established, applied to staff notifications instead of customer
    messages. Sent via `app.communications.providers.get_provider()`
    directly (recipient_reference = the staff member's own email/phone),
    not through a `Conversation`/`Message`/`CommunicationChannel` — those
    model customer-facing conversations, a mismatch for a one-off internal
    alert.
    """

    __tablename__ = "notification_delivery_attempts"
    __table_args__ = (
        CheckConstraint(f"channel IN {NOTIFICATION_DELIVERY_CHANNELS!r}", name="valid_channel"),
        CheckConstraint(f"status IN {NOTIFICATION_DELIVERY_STATUSES!r}", name="valid_status"),
        Index("ix_notification_delivery_attempts_notification_id", "notification_id"),
    )

    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notifications.id"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    provider_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
