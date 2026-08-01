"""Tests for `app.report_exports` — CSV formula-injection protection,
XLSX generation, and the export lifecycle end to end (against the real
storage adapter; skipped when Supabase Storage isn't configured)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from app.core.config import get_settings
from app.db.models import StaffUser
from app.report_exports.csv_writer import generate_csv
from app.report_exports.xlsx_writer import generate_xlsx
from app.reports import service as report_service
from app.reports.schemas import ReportDefinitionCreateIn
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def test_generate_csv_escapes_formula_injection() -> None:
    content = generate_csv(
        columns=["name", "note"],
        rows=[
            {"name": "=1+1", "note": "safe text"},
            {"name": "+1+1", "note": "-2+3"},
            {"name": "@SUM(A1:A2)", "note": None},
        ],
    ).decode("utf-8-sig")
    lines = content.splitlines()
    assert lines[0] == "name,note"
    assert lines[1] == "'=1+1,safe text"
    assert lines[2] == "'+1+1,'-2+3"
    assert lines[3] == "'@SUM(A1:A2),"


def test_generate_csv_leaves_ordinary_values_untouched() -> None:
    content = generate_csv(
        columns=["metric", "value"], rows=[{"metric": "Net sales", "value": 42800}]
    ).decode("utf-8-sig")
    assert "Net sales,42800" in content


def test_generate_xlsx_produces_nonempty_workbook() -> None:
    content = generate_xlsx(
        columns=["metric_code", "value"],
        rows=[{"metric_code": "exec_net_sales", "value": 42800}],
        sheet_title="Test Report",
    )
    assert content[:2] == b"PK"  # xlsx is a zip archive
    assert len(content) > 0


async def test_generate_export_fails_gracefully_without_dataset(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    from app.report_exports import service as export_service
    from app.report_exports.errors import ExportError

    owner = await make_staff_user()
    definition = await report_service.create_report_definition(
        db_session,
        actor=owner,
        payload=ReportDefinitionCreateIn(
            name="Export test report", domain="executive", metric_codes=["exec_net_sales"]
        ),
    )
    run, _results = await report_service.execute_report(
        db_session,
        actor=owner,
        definition=definition,
        permissions=frozenset({"analytics.executive.view"}),
        window_code="current_month",
        custom_start=None,
        custom_end=None,
    )

    if not get_settings().supabase_url:
        pytest.skip("Supabase Storage not configured in this environment")

    artifact = await export_service.generate_export(
        db_session, actor=owner, report_run=run, export_format="csv"
    )
    assert artifact.status == "completed"
    assert artifact.checksum_sha256 is not None
    assert artifact.row_count == 1

    with pytest.raises(ExportError):
        await export_service.generate_export(
            db_session,
            actor=owner,
            report_run=run,
            export_format="docx",  # type: ignore[arg-type]
        )
