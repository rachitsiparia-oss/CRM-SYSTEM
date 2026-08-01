import uuid
from datetime import datetime, time

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    AppendOnlyTimestampMixin,
    AuditedMixin,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.db.models.export_artifact import EXPORT_FORMATS

SCHEDULE_FREQUENCIES = ("daily", "weekly", "monthly")
DELIVERY_CHANNELS = ("email",)
DELIVERY_STATUSES = ("pending", "sent", "delivered", "failed")


class ScheduledReport(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A recurring report configuration — GROWTH_AND_INTELLIGENCE.md
    section 13.19. `is_enabled` defaults to `False`: seeded examples stay
    disabled by default (Phase 14 instruction section 19 seed-data rule),
    and live recurring dispatch is deferred to Phase 15's `apps/worker`
    cron wiring regardless of this flag — this table only defines *what*
    would run and *when*, matching the "engine, not scheduler" split.
    `execute_due_occurrence()` in `app.report_schedules.service` is the
    deterministic, idempotent, directly-callable execution function Phase
    15 will register on a timer.
    """

    __tablename__ = "scheduled_reports"
    __table_args__ = (
        CheckConstraint(f"schedule_frequency IN {SCHEDULE_FREQUENCIES!r}", name="valid_frequency"),
        CheckConstraint(f"output_format IN {EXPORT_FORMATS!r}", name="valid_output_format"),
        CheckConstraint(
            "schedule_day_of_week IS NULL OR schedule_day_of_week BETWEEN 0 AND 6",
            name="valid_day_of_week",
        ),
        CheckConstraint(
            "schedule_day_of_month IS NULL OR schedule_day_of_month BETWEEN 1 AND 28",
            name="valid_day_of_month",
        ),
        CheckConstraint(
            "(schedule_frequency != 'weekly') OR (schedule_day_of_week IS NOT NULL)",
            name="weekly_requires_day_of_week",
        ),
        CheckConstraint(
            "(schedule_frequency != 'monthly') OR (schedule_day_of_month IS NOT NULL)",
            name="monthly_requires_day_of_month",
        ),
        Index("ix_scheduled_reports_report_definition_id", "report_definition_id"),
        Index("ix_scheduled_reports_is_enabled", "is_enabled"),
    )

    report_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_definitions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    schedule_frequency: Mapped[str] = mapped_column(String(8), nullable=False)
    schedule_day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_time_of_day: Mapped[time] = mapped_column(Time, nullable=False, default=time(6, 0))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    output_format: Mapped[str] = mapped_column(String(8), nullable=False, default="pdf")
    fixed_filters: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    include_ai_narrative: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)


class ScheduledReportRecipient(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """A resolved recipient of a scheduled report. Deliberately a child
    table rather than a JSON array on `ScheduledReport` so recipients keep
    real FK integrity to `staff_users`/role codes (CLAUDE.md's "avoid
    unbounded JSON blobs for core searchable or relational business data").

    `recipient_email_override` covers PROJECT_PLAN.md's "owner email
    delivery with configurable recipients" case where the intended address
    (e.g. a finance mailbox) has no backing `staff_users` row — CLAUDE.md
    section 23's "report-recipient addresses belong in Settings and must
    not be hardcoded" is satisfied by making this a per-schedule,
    UI-editable row rather than a literal constant anywhere in code.
    """

    __tablename__ = "scheduled_report_recipients"
    __table_args__ = (
        CheckConstraint(
            "(recipient_staff_id IS NOT NULL)::int + (recipient_role_code IS NOT NULL)::int "
            "+ (recipient_email_override IS NOT NULL)::int = 1",
            name="exactly_one_recipient_target",
        ),
        Index("ix_scheduled_report_recipients_scheduled_report_id", "scheduled_report_id"),
    )

    scheduled_report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheduled_reports.id"), nullable=False
    )
    recipient_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    recipient_role_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recipient_email_override: Mapped[str | None] = mapped_column(String(320), nullable=True)


class ReportDeliveryAttempt(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """The idempotent delivery ledger — GROWTH_AND_INTELLIGENCE.md section
    13.19 ("permission must be checked at generation and delivery time").
    `occurrence_key` (e.g. `f"{scheduled_report_id}:{period_label}"`) plus
    `recipient_reference` (the resolved address/staff id snapshotted at
    delivery time, not a live FK dereference) form the dedup key, matching
    `ComplaintEscalation.dedup_key`'s established idempotency pattern.
    Delivery itself goes through the existing Communication Hub provider
    abstraction (`app.communications`), never a bespoke email client.
    """

    __tablename__ = "report_delivery_attempts"
    __table_args__ = (
        CheckConstraint(
            # `!r` on a 1-tuple renders `('email',)`, a trailing-comma
            # syntax error in SQL — join elements explicitly instead so
            # this stays correct as `DELIVERY_CHANNELS` grows.
            "delivery_channel IN (" + ", ".join(repr(c) for c in DELIVERY_CHANNELS) + ")",
            name="valid_delivery_channel",
        ),
        CheckConstraint(f"status IN {DELIVERY_STATUSES!r}", name="valid_status"),
        Index(
            "uq_report_delivery_attempts_occurrence",
            "scheduled_report_id",
            "occurrence_key",
            "recipient_reference",
            unique=True,
        ),
    )

    scheduled_report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scheduled_reports.id"), nullable=False
    )
    report_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("report_runs.id"), nullable=True
    )
    export_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("export_artifacts.id"), nullable=True
    )
    occurrence_key: Mapped[str] = mapped_column(String(160), nullable=False)
    recipient_reference: Mapped[str] = mapped_column(String(320), nullable=False)
    delivery_channel: Mapped[str] = mapped_column(String(16), nullable=False, default="email")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_details: Mapped[str | None] = mapped_column(Text, nullable=True)
