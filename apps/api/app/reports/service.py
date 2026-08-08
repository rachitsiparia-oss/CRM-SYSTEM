"""Report definition CRUD/sharing, deterministic report execution, live
dashboard aggregation, and a small allowlisted drill-down surface — all
built exclusively on `app.analytics_core.engine.run_metric_query`, never a
second, parallel query path (GROWTH_AND_INTELLIGENCE.md section 13.1's
"must not become an unrestricted query engine over raw production
tables").
"""

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.engine import MetricResult, run_metric_query
from app.analytics_core.registry import get_metric, metrics_for_domain
from app.analytics_core.windows import RESTAURANT_TIMEZONE, ResolvedWindow, resolve_window
from app.core.pagination import DEFAULT_PAGE_SIZE
from app.db.models import (
    Complaint,
    InventoryItem,
    Lead,
    Order,
    ReportDefinition,
    ReportDefinitionShare,
    ReportRun,
    ReportRunDataset,
    Reservation,
    Role,
    StaffRole,
    StaffUser,
    TaskRecord,
)
from app.reports.errors import (
    InvalidMetricSelectionError,
    MetricPermissionDeniedForReportError,
    ReportDefinitionNotEditableError,
)

_DRILLDOWN_LIMIT = 100


def _generate_report_code(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "report"
    return f"{slug[:60]}-{uuid.uuid4().hex[:8]}"


def _metric_result_dict(result: MetricResult) -> dict[str, object]:
    return {
        "metric_code": result.metric.code,
        "display_name": result.metric.display_name,
        "value_type": result.metric.value_type,
        "unit": result.metric.unit,
        "value": float(result.value),
        "comparison_value": float(result.comparison_value)
        if result.comparison_value is not None
        else None,
        "change_pct": float(result.change_pct) if result.change_pct is not None else None,
        "freshness": result.metric.freshness,
    }


async def _actor_role_codes(session: AsyncSession, staff_user_id: uuid.UUID) -> frozenset[str]:
    rows = await session.scalars(
        select(Role.code)
        .join(StaffRole, StaffRole.role_id == Role.id)
        .where(StaffRole.staff_user_id == staff_user_id, Role.is_active.is_(True))
    )
    return frozenset(rows.all())


async def can_access_definition(
    session: AsyncSession,
    *,
    actor: StaffUser,
    definition: ReportDefinition,
    level: str = "view",
) -> bool:
    if definition.visibility == "system":
        return True
    if definition.owner_staff_id == actor.id:
        return True
    if definition.visibility != "shared":
        return False
    role_codes = await _actor_role_codes(session, actor.id)
    shares = await session.scalars(
        select(ReportDefinitionShare).where(
            ReportDefinitionShare.report_definition_id == definition.id
        )
    )
    for share in shares.all():
        matches_target = share.shared_with_staff_id == actor.id or (
            share.shared_with_role_code is not None and share.shared_with_role_code in role_codes
        )
        if not matches_target:
            continue
        if level == "view":
            return True
        if level == "run" and share.permission_level in ("view", "run"):
            return True
    return False


def _validate_metric_codes(metric_codes: list[str]) -> None:
    for code in metric_codes:
        try:
            get_metric(code)
        except KeyError as exc:
            raise InvalidMetricSelectionError(f"Unknown metric code: {code!r}") from exc


async def create_report_definition(
    session: AsyncSession, *, actor: StaffUser, payload: object
) -> ReportDefinition:
    from app.reports.schemas import ReportDefinitionCreateIn

    assert isinstance(payload, ReportDefinitionCreateIn)
    _validate_metric_codes(payload.metric_codes)
    definition = ReportDefinition(
        code=_generate_report_code(payload.name),
        name=payload.name,
        description=payload.description,
        domain=payload.domain,
        definition_type="custom",
        metric_codes=payload.metric_codes,
        dimensions=payload.dimensions,
        default_filters=payload.default_filters,
        default_window=payload.default_window,
        comparison_enabled=payload.comparison_enabled,
        owner_staff_id=actor.id,
        visibility=payload.visibility,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(definition)
    await session.flush()
    return definition


async def update_report_definition(
    session: AsyncSession, *, actor: StaffUser, definition: ReportDefinition, payload: object
) -> ReportDefinition:
    from app.reports.schemas import ReportDefinitionUpdateIn

    assert isinstance(payload, ReportDefinitionUpdateIn)
    is_owner = definition.owner_staff_id == actor.id
    if definition.definition_type == "system" or not is_owner:
        raise ReportDefinitionNotEditableError(
            "Only the owner may edit a custom report definition; system definitions "
            "require reports.manage_system."
        )
    if payload.metric_codes is not None:
        _validate_metric_codes(payload.metric_codes)
        definition.metric_codes = payload.metric_codes
    for field_name in (
        "name",
        "description",
        "dimensions",
        "default_filters",
        "default_window",
        "comparison_enabled",
        "visibility",
        "is_active",
    ):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(definition, field_name, value)
    definition.updated_by = actor.id
    definition.version += 1
    await session.flush()
    return definition


async def share_report_definition(
    session: AsyncSession, *, actor: StaffUser, definition: ReportDefinition, payload: object
) -> ReportDefinitionShare:
    from app.reports.schemas import ReportDefinitionShareIn

    assert isinstance(payload, ReportDefinitionShareIn)
    share = ReportDefinitionShare(
        report_definition_id=definition.id,
        shared_with_staff_id=payload.shared_with_staff_id,
        shared_with_role_code=payload.shared_with_role_code,
        permission_level=payload.permission_level,
        created_by=actor.id,
    )
    session.add(share)
    if definition.visibility != "shared":
        definition.visibility = "shared"
    await session.flush()
    return share


async def get_report_definition(
    session: AsyncSession, definition_id: uuid.UUID
) -> ReportDefinition | None:
    return await session.get(ReportDefinition, definition_id)


async def list_report_definitions(
    session: AsyncSession,
    *,
    actor: StaffUser,
    domain: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[ReportDefinition], int]:
    role_codes = await _actor_role_codes(session, actor.id)
    conditions: list[ColumnElement[bool]] = [ReportDefinition.is_active.is_(True)]
    if domain is not None:
        conditions.append(ReportDefinition.domain == domain)

    visible_ids_stmt = select(ReportDefinition.id).where(
        *conditions,
        (ReportDefinition.visibility == "system")
        | (ReportDefinition.owner_staff_id == actor.id)
        | (
            ReportDefinition.id.in_(
                select(ReportDefinitionShare.report_definition_id).where(
                    (ReportDefinitionShare.shared_with_staff_id == actor.id)
                    | (ReportDefinitionShare.shared_with_role_code.in_(role_codes))
                )
            )
        ),
    )
    total = (
        await session.scalar(select(func.count()).select_from(visible_ids_stmt.subquery()))
    ) or 0
    rows = (
        await session.scalars(
            select(ReportDefinition)
            .where(ReportDefinition.id.in_(visible_ids_stmt))
            .order_by(ReportDefinition.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return list(rows), total


async def execute_report(
    session: AsyncSession,
    *,
    actor: StaffUser,
    definition: ReportDefinition,
    permissions: frozenset[str],
    window_code: str,
    custom_start: datetime | None,
    custom_end: datetime | None,
    trigger_source: str = "manual",
) -> tuple[ReportRun, list[MetricResult]]:
    window = resolve_window(window_code, custom_start=custom_start, custom_end=custom_end)

    run = ReportRun(
        report_definition_id=definition.id,
        requested_by_staff_id=actor.id if trigger_source == "manual" else None,
        trigger_source=trigger_source,
        status="running",
        window_code=window.window_code,
        window_start=window.start,
        window_end=window.end,
        comparison_window_start=window.comparison_start,
        comparison_window_end=window.comparison_end,
        timezone=window.timezone,
        filters_snapshot=definition.default_filters,
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()

    results: list[MetricResult] = []
    metric_versions: dict[str, int] = {}
    try:
        for metric_code in definition.metric_codes:
            metric = get_metric(metric_code)
            if metric.required_permission not in permissions:
                raise MetricPermissionDeniedForReportError(
                    f"Missing {metric.required_permission!r} required for metric {metric_code!r}."
                )
            result = await run_metric_query(
                session,
                metric_code=metric_code,
                permissions=permissions,
                window_code=window_code,
                custom_start=custom_start,
                custom_end=custom_end,
                include_comparison=definition.comparison_enabled,
            )
            results.append(result)
            metric_versions[metric_code] = metric.version
    except Exception as exc:
        run.status = "failed"
        run.failure_details = str(exc)
        run.completed_at = datetime.now(UTC)
        await session.flush()
        raise

    dataset_payload = {"metrics": [_metric_result_dict(r) for r in results]}
    checksum = hashlib.sha256(
        json.dumps(dataset_payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    run.status = "completed"
    run.row_count = len(results)
    run.checksum_sha256 = checksum
    run.metric_versions_snapshot = metric_versions
    run.completed_at = datetime.now(UTC)
    await session.flush()

    dataset = ReportRunDataset(
        report_run_id=run.id,
        result_data=dataset_payload,
        summary={"metric_count": len(results)},
    )
    session.add(dataset)
    await session.flush()

    return run, results


async def get_report_run(session: AsyncSession, run_id: uuid.UUID) -> ReportRun | None:
    return await session.get(ReportRun, run_id)


async def get_report_run_dataset(
    session: AsyncSession, run_id: uuid.UUID
) -> ReportRunDataset | None:
    result: ReportRunDataset | None = await session.scalar(
        select(ReportRunDataset).where(ReportRunDataset.report_run_id == run_id)
    )
    return result


async def list_report_runs(
    session: AsyncSession,
    *,
    report_definition_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[ReportRun], int]:
    conditions = []
    if report_definition_id is not None:
        conditions.append(ReportRun.report_definition_id == report_definition_id)
    total = (
        await session.scalar(select(func.count()).select_from(ReportRun).where(*conditions))
    ) or 0
    rows = (
        await session.scalars(
            select(ReportRun)
            .where(*conditions)
            .order_by(ReportRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return list(rows), total


async def get_dashboard(
    session: AsyncSession,
    *,
    domain: str,
    permissions: frozenset[str],
    window_code: str,
    custom_start: datetime | None,
    custom_end: datetime | None,
) -> tuple[ResolvedWindow, list[MetricResult], list[str]]:
    """Every metric in the domain the caller can see is included; metrics
    the caller lacks permission for are silently skipped rather than
    failing the whole dashboard — GROWTH_AND_INTELLIGENCE.md section
    16.5's "partial failures do not blank the whole dashboard"."""
    window = resolve_window(window_code, custom_start=custom_start, custom_end=custom_end)
    results: list[MetricResult] = []
    skipped: list[str] = []
    for metric in metrics_for_domain(domain):
        if metric.required_permission not in permissions:
            skipped.append(metric.code)
            continue
        result = await run_metric_query(
            session,
            metric_code=metric.code,
            permissions=permissions,
            window_code=window_code,
            custom_start=custom_start,
            custom_end=custom_end,
        )
        results.append(result)
    return window, results, skipped


# Phase 17.5's own instruction: bounded the same way MAX_CUSTOM_RANGE_DAYS
# bounds a custom report window — a chart never scans unbounded history.
MAX_TIMESERIES_DAYS = 90


async def get_metric_timeseries(
    session: AsyncSession, *, metric_code: str, days: int
) -> list[tuple[str, float]]:
    """Daily values for `metric_code`, oldest first, ending yesterday — the
    router has already 404/403'd an unknown or unpermitted metric_code via
    `require_metric_permission_or_404` before this runs, matching
    `get_drilldown`'s split (router validates, service assumes valid
    input). Reuses `app.forecasts.data.get_daily_history`, the same
    per-day windowing this codebase already built for forecasting, rather
    than a second date-bucketing implementation."""
    from app.forecasts.data import get_daily_history

    values = await get_daily_history(session, metric_code, num_days=days)
    today_local = datetime.now(UTC).astimezone(RESTAURANT_TIMEZONE).date()
    dates = [today_local - timedelta(days=d) for d in range(days, 0, -1)]
    return [(d.isoformat(), float(v)) for d, v in zip(dates, values, strict=True)]


# Drill-down — a deliberately small, hand-written allowlist rather than a
# generic per-metric drill-down mechanism (this phase's own scoping
# decision, documented in DATABASE_AND_API.md's Phase 14 notes).
async def get_drilldown(
    session: AsyncSession, *, metric_code: str, window: ResolvedWindow
) -> list[dict[str, object]]:
    if metric_code == "exec_open_high_severity_complaints":
        complaint_rows = (
            await session.scalars(
                select(Complaint)
                .where(
                    Complaint.severity.in_(("high", "critical")),
                    Complaint.status.not_in(("resolved", "closed", "cancelled")),
                    Complaint.created_at < window.end,
                )
                .order_by(Complaint.created_at.desc())
                .limit(_DRILLDOWN_LIMIT)
            )
        ).all()
        return [
            {
                "record_type": "complaint",
                "record_id": str(r.id),
                "label": r.complaint_number,
                "detail": {"severity": r.severity, "status": r.status, "title": r.title},
            }
            for r in complaint_rows
        ]
    if metric_code == "leads_open":
        lead_rows = (
            await session.scalars(
                select(Lead)
                .where(
                    Lead.deleted_at.is_(None),
                    Lead.status.not_in(("won", "lost", "closed")),
                    Lead.created_at < window.end,
                )
                .order_by(Lead.created_at.desc())
                .limit(_DRILLDOWN_LIMIT)
            )
        ).all()
        return [
            {
                "record_type": "lead",
                "record_id": str(r.id),
                "label": r.display_name,
                "detail": {"status": r.status, "source": r.source},
            }
            for r in lead_rows
        ]
    if metric_code in ("inventory_low_stock_items", "inventory_critical_stock_items"):
        target_status = "low_stock" if metric_code.startswith("inventory_low") else "critical_stock"
        item_rows = (
            await session.scalars(
                select(InventoryItem)
                .where(
                    InventoryItem.deleted_at.is_(None),
                    InventoryItem.is_active.is_(True),
                    InventoryItem.stock_status == target_status,
                )
                .order_by(InventoryItem.name)
                .limit(_DRILLDOWN_LIMIT)
            )
        ).all()
        return [
            {
                "record_type": "inventory_item",
                "record_id": str(r.id),
                "label": r.name,
                "detail": {"current_stock": str(r.current_stock), "stock_status": r.stock_status},
            }
            for r in item_rows
        ]
    if metric_code == "sales_cancelled_order_count":
        order_rows = (
            await session.scalars(
                select(Order)
                .where(
                    Order.status == "cancelled",
                    Order.created_at >= window.start,
                    Order.created_at < window.end,
                )
                .order_by(Order.created_at.desc())
                .limit(_DRILLDOWN_LIMIT)
            )
        ).all()
        return [
            {
                "record_type": "order",
                "record_id": str(r.id),
                "label": r.order_number,
                "detail": {"status": r.status, "grand_total_minor": r.grand_total_minor},
            }
            for r in order_rows
        ]
    if metric_code == "staff_overdue_tasks":
        task_rows = (
            await session.scalars(
                select(TaskRecord)
                .where(
                    TaskRecord.status.not_in(("completed", "cancelled")),
                    TaskRecord.due_at.is_not(None),
                    TaskRecord.due_at < window.end,
                )
                .order_by(TaskRecord.due_at)
                .limit(_DRILLDOWN_LIMIT)
            )
        ).all()
        return [
            {
                "record_type": "task",
                "record_id": str(r.id),
                "label": r.title,
                "detail": {
                    "status": r.status,
                    "due_at": r.due_at.isoformat() if r.due_at else None,
                },
            }
            for r in task_rows
        ]
    if metric_code == "reservations_no_show_rate":
        reservation_rows = (
            await session.scalars(
                select(Reservation)
                .where(
                    Reservation.status == "no_show",
                    Reservation.created_at >= window.start,
                    Reservation.created_at < window.end,
                )
                .order_by(Reservation.created_at.desc())
                .limit(_DRILLDOWN_LIMIT)
            )
        ).all()
        return [
            {
                "record_type": "reservation",
                "record_id": str(r.id),
                "label": str(r.id),
                "detail": {"party_size": r.party_size, "status": r.status},
            }
            for r in reservation_rows
        ]
    raise InvalidMetricSelectionError(f"Drill-down is not available for metric {metric_code!r}.")
