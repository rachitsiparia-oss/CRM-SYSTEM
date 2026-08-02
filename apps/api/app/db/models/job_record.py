from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

JOB_STATUSES = (
    "scheduled",
    "pending",
    "queued",
    "running",
    "retry_wait",
    "succeeded",
    "failed_permanent",
    "cancelled",
    "dead_lettered",
)
# INTEGRATIONS_AUTOMATIONS_REALTIME.md section 10.4/10.5 — Phase 15 adds
# `queue_name`/`priority` to the Phase 3 foundation table rather than
# creating a second job table; both were anticipated in the docstring
# ("durable business record of ARQ job execution") but never given columns
# since nothing constructed a JobRecord before this phase.
JOB_QUEUE_NAMES = (
    "critical-domain",
    "communications",
    "campaigns",
    "reports",
    "exports",
    "integrations",
    "ai",
    "maintenance",
)
JOB_PRIORITIES = ("critical", "high", "normal", "low", "maintenance")


class JobRecord(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Durable business record of ARQ job execution —
    ARCHITECTURE_AND_TECH_STACK.md section 12.1, DATABASE_AND_API.md
    section 16.7, TOOLS.md section 7.3.

    ARQ and Redis coordinate *execution*; this table is the durable source
    of truth for job status, retries, and results — Redis is never the only
    copy of business-critical state (CLAUDE.md section 7).
    """

    __tablename__ = "job_records"
    __table_args__ = (
        CheckConstraint(f"status IN {JOB_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"queue_name IN {JOB_QUEUE_NAMES!r}", name="valid_queue_name"),
        CheckConstraint(f"priority IN {JOB_PRIORITIES!r}", name="valid_priority"),
        UniqueConstraint("idempotency_key", name="uq_job_records_idempotency_key"),
        Index("ix_job_records_status_retry", "status", "next_retry_at"),
        Index("ix_job_records_queue_status", "queue_name", "status"),
    )

    job_type: Mapped[str] = mapped_column(String(120), nullable=False)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    queue_name: Mapped[str] = mapped_column(String(32), nullable=False, default="maintenance")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    payload_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    progress: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
