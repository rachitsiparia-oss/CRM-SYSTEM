import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

# CLAUDE.md section 14 / this phase's own instruction section 20 — failure
# classification vocabulary, closed rather than free text so retry logic can
# switch on it deterministically.
DELIVERY_ATTEMPT_RESULTS = (
    "success",
    "transient_failure",
    "rate_limited",
    "invalid_destination",
    "authentication_error",
    "template_rejected",
    "suppressed",
    "customer_opted_out",
    "permanent_failure",
    "network_timeout",
)


class MessageDeliveryAttempt(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """One row per send attempt against a provider — a retry creates a new
    row rather than mutating the last one, so the full attempt history
    (CLAUDE.md section 20, "Retries create traceable attempts") survives."""

    __tablename__ = "message_delivery_attempts"
    __table_args__ = (
        CheckConstraint(f"result IN {DELIVERY_ATTEMPT_RESULTS!r}", name="valid_result"),
        CheckConstraint("attempt_number > 0", name="valid_attempt_number"),
        Index("ix_message_delivery_attempts_message_id", "message_id"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_response_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
