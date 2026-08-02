from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


class OperationalSettings(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Global, single-row operational configuration for the background job
    and scheduler system — same constant-unique-column singleton guard as
    `ReservationSettings`/`ReservationPolicies` (Phase 9). Holds tunable
    operational knobs, not business rules: retry/backoff defaults, worker
    concurrency limits, queue priority weighting, which notification
    channels are currently permitted to send, and maintenance mode.
    Changing any field here never bypasses a domain state-machine rule or
    permission check — it only tunes how the job/scheduler infrastructure
    behaves.
    """

    __tablename__ = "operational_settings"
    __table_args__ = (
        CheckConstraint("singleton_guard", name="valid_singleton_guard"),
        CheckConstraint("default_max_attempts > 0", name="valid_default_max_attempts"),
        CheckConstraint(
            "default_retry_backoff_seconds > 0", name="valid_default_retry_backoff_seconds"
        ),
        CheckConstraint(
            "default_retry_backoff_cap_seconds >= default_retry_backoff_seconds",
            name="valid_default_retry_backoff_cap_seconds",
        ),
        CheckConstraint("worker_max_jobs > 0", name="valid_worker_max_jobs"),
        CheckConstraint("worker_job_timeout_seconds > 0", name="valid_worker_job_timeout_seconds"),
    )

    singleton_guard: Mapped[bool] = mapped_column(
        Boolean, unique=True, nullable=False, default=True
    )
    maintenance_mode_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    maintenance_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduler_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    default_retry_backoff_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    default_retry_backoff_cap_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1800
    )
    worker_max_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    worker_job_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    queue_priority_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    notification_channel_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    active_ai_provider_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
