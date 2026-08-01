import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 11.6 — the outreach half of feedback:
# asking a customer to rate a completed, eligible order or visit. What they
# submit becomes a `FeedbackEntry` (via `resulting_feedback_id`); this table
# tracks only the request/delivery lifecycle, matching the "engine, not
# scheduler" split every prior phase's own reminder/scheduled-message
# system used — `process_due_review_requests` (app.feedback.review_requests)
# is a deterministic, idempotent, callable function; the live recurring
# dispatch through `apps/worker` is Phase 15's scope.
REVIEW_REQUEST_SOURCE_TYPES = ("order", "reservation")
REVIEW_REQUEST_CHANNELS = ("whatsapp", "email", "sms")
REVIEW_REQUEST_STATUSES = (
    "draft",
    "eligible",
    "scheduled",
    "sent",
    "delivered",
    "opened",
    "completed",
    "expired",
    "suppressed",
    "cancelled",
    "failed",
)


class ReviewRequest(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """`idempotency_key` is derived from `source_type:source_id` at
    creation time (one request per qualifying order/reservation, never
    re-issued even across a cooldown-eligible retry) — the same
    duplicate-request prevention every prior phase's scheduled-outreach
    system uses."""

    __tablename__ = "review_requests"
    __table_args__ = (
        CheckConstraint(
            f"source_type IN {REVIEW_REQUEST_SOURCE_TYPES!r}", name="valid_source_type"
        ),
        CheckConstraint(f"channel IN {REVIEW_REQUEST_CHANNELS!r}", name="valid_channel"),
        CheckConstraint(f"status IN {REVIEW_REQUEST_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "(source_type = 'order' AND order_id IS NOT NULL AND reservation_id IS NULL) OR "
            "(source_type = 'reservation' AND reservation_id IS NOT NULL AND order_id IS NULL)",
            name="valid_source_reference",
        ),
        Index("ix_review_requests_customer_id", "customer_id"),
        Index("ix_review_requests_status", "status"),
        Index("ix_review_requests_scheduled_at", "scheduled_at"),
        Index(
            "uq_review_requests_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id"), nullable=True
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    eligibility_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    suppression_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resulting_feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("feedback_entries.id"), nullable=True
    )
    scheduled_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scheduled_messages.id"), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
