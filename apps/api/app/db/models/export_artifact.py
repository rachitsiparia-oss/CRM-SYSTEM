import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

EXPORT_FORMATS = ("csv", "xlsx", "pdf")
EXPORT_STATUSES = ("pending", "generating", "completed", "failed")
EXPORT_SOURCES = ("report_run", "domain_direct")


class ExportArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A generated export file — GROWTH_AND_INTELLIGENCE.md section 13.18
    and TOOLS.md section 11 (CSV formula-injection protection required;
    openpyxl locked for XLSX; Playwright/Chromium locked for PDF).

    `export_source="domain_direct"` deliberately generalizes this table
    beyond report-run exports so it can also back the pre-existing,
    never-implemented `leads.export` permission (see
    DATABASE_AND_API.md's Phase 14 implementation notes) without a second,
    duplicate export-tracking table — CLAUDE.md's "avoid duplicating
    utilities" rule. `report_run_id` is then simply left null and the
    caller records enough context in `storage_path` naming to identify the
    source domain query.

    Not append-only: status progresses pending -> generating ->
    completed/failed, same lifecycle shape as `ReportRun`/`JobRecord`.
    `job_record_id` links to the generic `JobRecord` table when generation
    is large enough to go through the ARQ-style job-tracking path (the
    actual recurring worker registration is deferred to Phase 15, per the
    "engine, not scheduler" split already used in Phases 9/10/12/13).
    """

    __tablename__ = "export_artifacts"
    __table_args__ = (
        CheckConstraint(f"export_format IN {EXPORT_FORMATS!r}", name="valid_export_format"),
        CheckConstraint(f"status IN {EXPORT_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"export_source IN {EXPORT_SOURCES!r}", name="valid_export_source"),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0", name="non_negative_file_size"
        ),
        CheckConstraint("row_count IS NULL OR row_count >= 0", name="non_negative_row_count"),
        Index("ix_export_artifacts_requested_by_staff_id", "requested_by_staff_id", "created_at"),
        Index("ix_export_artifacts_status", "status"),
        Index("ix_export_artifacts_expires_at", "expires_at"),
        Index("ix_export_artifacts_report_run_id", "report_run_id"),
    )

    report_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("report_runs.id"), nullable=True
    )
    export_source: Mapped[str] = mapped_column(String(16), nullable=False, default="report_run")
    requested_by_staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_users.id"), nullable=False
    )
    export_format: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    job_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_records.id"), nullable=True
    )
    storage_bucket: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
