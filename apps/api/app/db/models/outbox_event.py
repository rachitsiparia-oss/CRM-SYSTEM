import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

OUTBOX_STATUSES = (
    "pending",
    "processing",
    "published",
    "failed_retryable",
    "failed_permanent",
    "cancelled",
)


class OutboxEvent(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Transactional outbox — ARCHITECTURE_AND_TECH_STACK.md section 12.4,
    DATABASE_AND_API.md section 16.6.

    Written in the same database transaction as the business change it
    describes, then dispatched by a worker. Never send external
    communication inside an uncommitted transaction — CLAUDE.md section 14.
    """

    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint(f"status IN {OUTBOX_STATUSES!r}", name="valid_status"),
        UniqueConstraint("idempotency_key", name="uq_outbox_events_idempotency_key"),
        Index("ix_outbox_events_status_available", "status", "available_at"),
    )

    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
