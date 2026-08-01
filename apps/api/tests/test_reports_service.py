"""Tests for `app.reports.service` — report definition CRUD/sharing scope,
deterministic report execution and immutability, live dashboard
aggregation, and the allowlisted drill-down surface."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from app.db.models import StaffUser
from app.reports import service
from app.reports.errors import ReportDefinitionNotEditableError
from app.reports.schemas import (
    ReportDefinitionCreateIn,
    ReportDefinitionShareIn,
    ReportDefinitionUpdateIn,
)
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]
_ALL_PERMISSIONS = frozenset(
    {
        "analytics.executive.view",
        "analytics.sales.view",
        "reports.view",
        "reports.create",
        "reports.run",
        "reports.share",
    }
)


async def test_create_report_definition_rejects_unknown_metric(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user()
    with pytest.raises(Exception):  # noqa: B017 - InvalidMetricSelectionError from validate
        await service.create_report_definition(
            db_session,
            actor=owner,
            payload=ReportDefinitionCreateIn(
                name="Bad report",
                domain="executive",
                metric_codes=["not_a_real_metric"],
            ),
        )


async def test_create_and_run_report_produces_immutable_run(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user()
    definition = await service.create_report_definition(
        db_session,
        actor=owner,
        payload=ReportDefinitionCreateIn(
            name="My exec overview",
            domain="executive",
            metric_codes=["exec_net_sales", "exec_completed_orders"],
            visibility="private",
        ),
    )
    assert definition.definition_type == "custom"
    assert definition.code

    run, results = await service.execute_report(
        db_session,
        actor=owner,
        definition=definition,
        permissions=_ALL_PERMISSIONS,
        window_code="current_month",
        custom_start=None,
        custom_end=None,
    )
    assert run.status == "completed"
    assert run.row_count == 2
    assert run.checksum_sha256 is not None
    assert {r.metric.code for r in results} == {"exec_net_sales", "exec_completed_orders"}

    dataset = await service.get_report_run_dataset(db_session, run.id)
    assert dataset is not None
    assert len(dataset.result_data["metrics"]) == 2


async def test_execute_report_denies_metric_outside_permission_scope(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user()
    definition = await service.create_report_definition(
        db_session,
        actor=owner,
        payload=ReportDefinitionCreateIn(
            name="Needs staff analytics",
            domain="staff_tasks",
            metric_codes=["staff_active_count"],
        ),
    )
    with pytest.raises(Exception):  # noqa: B017 - MetricPermissionDeniedForReportError
        await service.execute_report(
            db_session,
            actor=owner,
            definition=definition,
            permissions=frozenset({"reports.run"}),  # missing analytics.staff.view
            window_code="current_month",
            custom_start=None,
            custom_end=None,
        )


async def test_private_definition_not_visible_to_other_staff(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user()
    other = await make_staff_user()
    definition = await service.create_report_definition(
        db_session,
        actor=owner,
        payload=ReportDefinitionCreateIn(
            name="Private report",
            domain="executive",
            metric_codes=["exec_net_sales"],
            visibility="private",
        ),
    )
    assert await service.can_access_definition(db_session, actor=owner, definition=definition)
    assert not await service.can_access_definition(db_session, actor=other, definition=definition)


async def test_sharing_definition_grants_view_access(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user()
    recipient = await make_staff_user()
    definition = await service.create_report_definition(
        db_session,
        actor=owner,
        payload=ReportDefinitionCreateIn(
            name="Shared report",
            domain="executive",
            metric_codes=["exec_net_sales"],
            visibility="private",
        ),
    )
    await service.share_report_definition(
        db_session,
        actor=owner,
        definition=definition,
        payload=ReportDefinitionShareIn(shared_with_staff_id=recipient.id, permission_level="view"),
    )
    assert definition.visibility == "shared"
    assert await service.can_access_definition(db_session, actor=recipient, definition=definition)


async def test_update_report_definition_rejects_non_owner(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user()
    other = await make_staff_user()
    definition = await service.create_report_definition(
        db_session,
        actor=owner,
        payload=ReportDefinitionCreateIn(
            name="Owner only", domain="executive", metric_codes=["exec_net_sales"]
        ),
    )
    with pytest.raises(ReportDefinitionNotEditableError):
        await service.update_report_definition(
            db_session,
            actor=other,
            definition=definition,
            payload=ReportDefinitionUpdateIn(name="Hijacked"),
        )


async def test_get_dashboard_skips_metrics_without_permission(
    db_session: AsyncSession,
) -> None:
    window, results, skipped = await service.get_dashboard(
        db_session,
        domain="executive",
        permissions=frozenset({"analytics.executive.view"}),
        window_code="current_month",
        custom_start=None,
        custom_end=None,
    )
    assert window.window_code == "current_month"
    assert len(results) == 5  # all executive metrics
    assert skipped == []

    _window2, results2, skipped2 = await service.get_dashboard(
        db_session,
        domain="executive",
        permissions=frozenset(),
        window_code="current_month",
        custom_start=None,
        custom_end=None,
    )
    assert results2 == []
    assert len(skipped2) == 5


async def test_get_drilldown_unknown_metric_raises(db_session: AsyncSession) -> None:
    from app.analytics_core.windows import resolve_window
    from app.reports.errors import InvalidMetricSelectionError

    window = resolve_window("current_month")
    with pytest.raises(InvalidMetricSelectionError):
        await service.get_drilldown(db_session, metric_code="exec_net_sales", window=window)


async def test_get_drilldown_open_complaints_returns_records(
    db_session: AsyncSession,
) -> None:
    from app.analytics_core.windows import resolve_window

    window = resolve_window("current_month", now=datetime.now(UTC))
    records = await service.get_drilldown(
        db_session, metric_code="exec_open_high_severity_complaints", window=window
    )
    assert isinstance(records, list)
    for record in records:
        assert record["record_type"] == "complaint"
        assert "record_id" in record
