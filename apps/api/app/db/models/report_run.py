import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

REPORT_RUN_STATUSES = ("pending", "running", "completed", "failed")
REPORT_RUN_TRIGGER_SOURCES = ("manual", "scheduled", "system")


class ReportRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single execution of a `ReportDefinition` over a bounded window —
    GROWTH_AND_INTELLIGENCE.md section 13.17-13.18 and the Phase 14
    instruction's "report runs (immutable)" schema requirement.

    Uses `TimestampMixin`, not `AppendOnlyTimestampMixin`, because a run
    genuinely transitions pending -> running -> completed/failed before
    settling — the same lifecycle shape as `JobRecord`. Immutability is
    enforced at the service layer: once `status` reaches a terminal value,
    `app.reports.service` never issues a further UPDATE on that row. This
    mirrors the documented deviation already used for `ComplaintEscalation`
    and other "never edited after the fact, but not literally append-only
    mixin" tables in this codebase.
    """

    __tablename__ = "report_runs"
    __table_args__ = (
        CheckConstraint(f"status IN {REPORT_RUN_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            f"trigger_source IN {REPORT_RUN_TRIGGER_SOURCES!r}", name="valid_trigger_source"
        ),
        CheckConstraint("window_end >= window_start", name="valid_window_range"),
        CheckConstraint(
            "comparison_window_end IS NULL OR comparison_window_start IS NULL "
            "OR comparison_window_end >= comparison_window_start",
            name="valid_comparison_window_range",
        ),
        CheckConstraint("row_count IS NULL OR row_count >= 0", name="non_negative_row_count"),
        Index("ix_report_runs_report_definition_id", "report_definition_id"),
        Index("ix_report_runs_status", "status"),
        Index("ix_report_runs_requested_by_staff_id", "requested_by_staff_id"),
        Index("ix_report_runs_created_at", "created_at"),
    )

    report_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_definitions.id"), nullable=False
    )
    requested_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    trigger_source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    window_code: Mapped[str] = mapped_column(String(20), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comparison_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comparison_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    filters_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    metric_versions_snapshot: Mapped[dict[str, int] | None] = mapped_column(JSONB, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_details: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReportRunDataset(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """The bounded computed result of a completed `ReportRun` — written
    exactly once, immutably, when the run finalizes. Kept as its own table
    (rather than a JSON column on `ReportRun`) so the mutable run-lifecycle
    row and the immutable result payload have independent write patterns,
    per the instruction's explicit "report run datasets" schema entity.
    """

    __tablename__ = "report_run_datasets"
    __table_args__ = (Index("uq_report_run_datasets_report_run_id", "report_run_id", unique=True),)

    report_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_runs.id"), nullable=False)
    result_data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
