"""Reports and dashboard API — GROWTH_AND_INTELLIGENCE.md section 13. Metric
catalog and dashboard endpoints require only the relevant `analytics.*.view`
permission; report definition/run endpoints require the `reports.*`
permissions."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.engine import require_metric_permission_or_404
from app.analytics_core.registry import METRICS
from app.analytics_core.windows import REPORT_WINDOW_CODES, InvalidWindowError, resolve_window
from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import ReportDefinition, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.permissions.service import get_effective_permissions
from app.reports import service
from app.reports.errors import ReportError
from app.reports.schemas import (
    DashboardOut,
    DrilldownOut,
    DrilldownRecordOut,
    MetricDefOut,
    MetricResultOut,
    ReportDefinitionCreateIn,
    ReportDefinitionOut,
    ReportDefinitionShareIn,
    ReportDefinitionShareOut,
    ReportDefinitionUpdateIn,
    ReportRunDetailOut,
    ReportRunOut,
    ReportRunRequestIn,
)

router = APIRouter(prefix="/api/v1", tags=["reports"])

_DASHBOARD_DOMAINS = (
    "executive",
    "sales",
    "customers",
    "leads",
    "reservations",
    "inventory_suppliers",
    "marketing",
    "loyalty",
    "feedback",
    "complaints",
    "staff_tasks",
)


def _metric_result_out(result: object) -> MetricResultOut:
    from app.analytics_core.engine import MetricResult

    assert isinstance(result, MetricResult)
    return MetricResultOut(
        metric_code=result.metric.code,
        display_name=result.metric.display_name,
        value_type=result.metric.value_type,  # type: ignore[arg-type]
        unit=result.metric.unit,
        value=float(result.value),
        comparison_value=float(result.comparison_value)
        if result.comparison_value is not None
        else None,
        change_pct=float(result.change_pct) if result.change_pct is not None else None,
        window_code=result.window.window_code,
        window_start=result.window.start,
        window_end=result.window.end,
        comparison_start=result.window.comparison_start,
        comparison_end=result.window.comparison_end,
        freshness=result.metric.freshness,  # type: ignore[arg-type]
        generated_at=result.generated_at,
    )


async def _get_definition_or_404(
    session: AsyncSession, definition_id: uuid.UUID
) -> ReportDefinition:
    definition = await service.get_report_definition(session, definition_id)
    if definition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report definition not found.")
    return definition


@router.get("/analytics/metrics")
async def list_metrics(
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[MetricDefOut]]:
    """The report builder's server-provided capability metadata — the
    frontend never maintains its own duplicate metric catalog."""
    permissions = await get_effective_permissions(session, actor.id)
    visible = [m for m in METRICS if m.required_permission in permissions]
    return DataResponse(
        data=[
            MetricDefOut(
                code=m.code,
                display_name=m.display_name,
                description=m.description,
                domain=m.domain,  # type: ignore[arg-type]
                value_type=m.value_type,  # type: ignore[arg-type]
                unit=m.unit,
                required_permission=m.required_permission,
                supports_comparison=m.supports_comparison,
                freshness=m.freshness,  # type: ignore[arg-type]
                version=m.version,
            )
            for m in visible
        ],
        meta=request_meta(request),
    )


@router.get("/dashboard/{domain}")
async def get_dashboard(
    domain: str,
    request: Request,
    window: str = Query(default="current_month"),
    custom_start: datetime | None = Query(default=None),
    custom_end: datetime | None = Query(default=None),
    actor: StaffUser = Depends(require_permission("reports.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DashboardOut]:
    if domain not in _DASHBOARD_DOMAINS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown dashboard domain.")
    if window not in REPORT_WINDOW_CODES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unknown report window.")
    permissions = await get_effective_permissions(session, actor.id)
    try:
        resolved, results, skipped = await service.get_dashboard(
            session,
            domain=domain,
            permissions=permissions,
            window_code=window,
            custom_start=custom_start,
            custom_end=custom_end,
        )
    except InvalidWindowError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DataResponse(
        data=DashboardOut(
            domain=domain,
            window_code=resolved.window_code,
            window_start=resolved.start,
            window_end=resolved.end,
            metrics=[_metric_result_out(r) for r in results],
            partial_failures=skipped,
        ),
        meta=request_meta(request),
    )


@router.get("/reports/drilldown")
async def get_drilldown(
    request: Request,
    metric_code: str = Query(...),
    window: str = Query(default="current_month"),
    custom_start: datetime | None = Query(default=None),
    custom_end: datetime | None = Query(default=None),
    actor: StaffUser = Depends(require_permission("reports.drilldown.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DrilldownOut]:
    permissions = await get_effective_permissions(session, actor.id)
    require_metric_permission_or_404(metric_code, permissions)
    try:
        resolved = resolve_window(window, custom_start=custom_start, custom_end=custom_end)
        records = await service.get_drilldown(session, metric_code=metric_code, window=resolved)
    except (InvalidWindowError, ReportError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DataResponse(
        data=DrilldownOut(
            metric_code=metric_code,
            window_code=resolved.window_code,
            window_start=resolved.start,
            window_end=resolved.end,
            records=[DrilldownRecordOut(**r) for r in records],  # type: ignore[arg-type]
            truncated=len(records) >= service._DRILLDOWN_LIMIT,
        ),
        meta=request_meta(request),
    )


@router.get("/reports/definitions")
async def list_report_definitions(
    request: Request,
    domain: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    actor: StaffUser = Depends(require_permission("reports.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReportDefinitionOut]:
    rows, total = await service.list_report_definitions(
        session, actor=actor, domain=domain, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=[ReportDefinitionOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/reports/definitions", status_code=status.HTTP_201_CREATED)
async def create_report_definition(
    payload: ReportDefinitionCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReportDefinitionOut]:
    try:
        definition = await service.create_report_definition(session, actor=actor, payload=payload)
    except ReportError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=ReportDefinitionOut.model_validate(definition), meta=request_meta(request)
    )


@router.get("/reports/definitions/{definition_id}")
async def get_report_definition(
    definition_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReportDefinitionOut]:
    definition = await _get_definition_or_404(session, definition_id)
    if not await service.can_access_definition(session, actor=actor, definition=definition):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You cannot view this report.")
    return DataResponse(
        data=ReportDefinitionOut.model_validate(definition), meta=request_meta(request)
    )


@router.patch("/reports/definitions/{definition_id}")
async def update_report_definition(
    definition_id: uuid.UUID,
    payload: ReportDefinitionUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReportDefinitionOut]:
    definition = await _get_definition_or_404(session, definition_id)
    try:
        definition = await service.update_report_definition(
            session, actor=actor, definition=definition, payload=payload
        )
    except ReportError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=ReportDefinitionOut.model_validate(definition), meta=request_meta(request)
    )


@router.post("/reports/definitions/{definition_id}/share", status_code=status.HTTP_201_CREATED)
async def share_report_definition(
    definition_id: uuid.UUID,
    payload: ReportDefinitionShareIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.share")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReportDefinitionShareOut]:
    definition = await _get_definition_or_404(session, definition_id)
    if definition.owner_staff_id != actor.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only the owner may share this report."
        )
    share = await service.share_report_definition(
        session, actor=actor, definition=definition, payload=payload
    )
    return DataResponse(
        data=ReportDefinitionShareOut.model_validate(share), meta=request_meta(request)
    )


@router.post("/reports/definitions/{definition_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_report(
    definition_id: uuid.UUID,
    payload: ReportRunRequestIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.run")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReportRunDetailOut]:
    definition = await _get_definition_or_404(session, definition_id)
    if not await service.can_access_definition(
        session, actor=actor, definition=definition, level="run"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You cannot run this report.")
    permissions = await get_effective_permissions(session, actor.id)
    try:
        run, results = await service.execute_report(
            session,
            actor=actor,
            definition=definition,
            permissions=permissions,
            window_code=payload.window_code,
            custom_start=payload.custom_start,
            custom_end=payload.custom_end,
        )
    except (InvalidWindowError, ReportError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DataResponse(
        data=ReportRunDetailOut(
            run=ReportRunOut.model_validate(run),
            metrics=[_metric_result_out(r) for r in results],
            summary={"metric_count": len(results)},
        ),
        meta=request_meta(request),
    )


@router.get("/reports/runs")
async def list_report_runs(
    request: Request,
    report_definition_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("reports.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReportRunOut]:
    rows, total = await service.list_report_runs(
        session, report_definition_id=report_definition_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=[ReportRunOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/reports/runs/{run_id}")
async def get_report_run(
    run_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("reports.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReportRunDetailOut]:
    run = await service.get_report_run(session, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report run not found.")
    dataset = await service.get_report_run_dataset(session, run_id)
    metrics = (dataset.result_data.get("metrics") if dataset else None) or []
    return DataResponse(
        data=ReportRunDetailOut(
            run=ReportRunOut.model_validate(run),
            metrics=[],
            summary={"raw_metrics": metrics, **(dataset.summary or {} if dataset else {})},
        ),
        meta=request_meta(request),
    )
