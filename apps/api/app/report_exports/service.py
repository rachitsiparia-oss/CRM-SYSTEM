"""Export orchestration — GROWTH_AND_INTELLIGENCE.md section 13.18's
8-step export workflow. Small exports (every export this phase produces —
a report run's metric set is capped at 25 rows by
`ReportDefinitionCreateIn.metric_codes`) execute directly within the
request; `job_record_id` stays available on `ExportArtifact` for when a
future large-export path needs the ARQ-backed job-tracking table.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ExportArtifact, ReportRun, ReportRunDataset, StaffUser
from app.report_exports.csv_writer import generate_csv
from app.report_exports.errors import (
    ExportError,
    ExportExpiredError,
    ExportNotReadyError,
    UnsupportedExportFormatError,
)
from app.report_exports.pdf_writer import generate_pdf
from app.report_exports.templates import build_report_html
from app.report_exports.xlsx_writer import generate_xlsx
from app.storage import service as storage_service

EXPORT_BUCKET = "report-exports"
EXPORT_EXPIRY_HOURS = 24
MAX_EXPORT_BYTES = 20 * 1024 * 1024
_CONTENT_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}
_COLUMNS = ["metric_code", "display_name", "value", "comparison_value", "change_pct", "unit"]


def _export_object_path(*, artifact_id: uuid.UUID, export_format: str) -> str:
    return f"exports/{artifact_id}.{export_format}"


async def _get_dataset(session: AsyncSession, report_run_id: uuid.UUID) -> ReportRunDataset | None:
    result: ReportRunDataset | None = await session.scalar(
        select(ReportRunDataset).where(ReportRunDataset.report_run_id == report_run_id)
    )
    return result


async def generate_export(
    session: AsyncSession, *, actor: StaffUser, report_run: ReportRun, export_format: str
) -> ExportArtifact:
    if export_format not in _CONTENT_TYPES:
        raise UnsupportedExportFormatError(f"Unsupported export format: {export_format!r}")

    dataset = await _get_dataset(session, report_run.id)
    if dataset is None:
        raise ExportError("This report run has no completed dataset to export.")
    raw_metrics = dataset.result_data.get("metrics", [])
    metrics: list[dict[str, object]] = raw_metrics if isinstance(raw_metrics, list) else []
    rows = [{column: m.get(column) for column in _COLUMNS} for m in metrics]

    artifact = ExportArtifact(
        report_run_id=report_run.id,
        export_source="report_run",
        requested_by_staff_id=actor.id,
        export_format=export_format,
        status="generating",
    )
    session.add(artifact)
    await session.flush()

    try:
        if export_format == "csv":
            content = generate_csv(columns=_COLUMNS, rows=rows)
        elif export_format == "xlsx":
            content = generate_xlsx(columns=_COLUMNS, rows=rows, sheet_title=report_run.window_code)
        else:
            html = build_report_html(
                title="RKPR Report Export",
                domain=str(report_run.report_definition_id),
                window_code=report_run.window_code,
                window_start=report_run.window_start.isoformat(),
                window_end=report_run.window_end.isoformat(),
                timezone=report_run.timezone,
                generated_at=datetime.now(UTC).isoformat(),
                metrics=metrics,
            )
            content = await generate_pdf(html=html)

        if len(content) > MAX_EXPORT_BYTES:
            raise ExportError(
                f"Export exceeds the {MAX_EXPORT_BYTES // (1024 * 1024)}MB size limit."
            )

        checksum = hashlib.sha256(content).hexdigest()
        path = _export_object_path(artifact_id=artifact.id, export_format=export_format)
        await storage_service.ensure_bucket_exists(bucket=EXPORT_BUCKET)
        await storage_service.upload_object(
            bucket=EXPORT_BUCKET,
            path=path,
            data=content,
            content_type=_CONTENT_TYPES[export_format],
        )
    except Exception as exc:
        artifact.status = "failed"
        artifact.failure_details = str(exc)
        await session.flush()
        raise

    artifact.status = "completed"
    artifact.storage_bucket = EXPORT_BUCKET
    artifact.storage_path = path
    artifact.file_size_bytes = len(content)
    artifact.row_count = len(rows)
    artifact.checksum_sha256 = checksum
    artifact.expires_at = datetime.now(UTC) + timedelta(hours=EXPORT_EXPIRY_HOURS)
    artifact.completed_at = datetime.now(UTC)
    await session.flush()
    return artifact


async def get_export_artifact(
    session: AsyncSession, artifact_id: uuid.UUID
) -> ExportArtifact | None:
    return await session.get(ExportArtifact, artifact_id)


async def get_download_url(artifact: ExportArtifact) -> str:
    if (
        artifact.status != "completed"
        or artifact.storage_path is None
        or artifact.storage_bucket is None
    ):
        raise ExportNotReadyError("This export is not ready for download.")
    if artifact.expires_at is not None and artifact.expires_at < datetime.now(UTC):
        raise ExportExpiredError("This export has expired.")
    return await storage_service.create_signed_url(
        bucket=artifact.storage_bucket, path=artifact.storage_path
    )
