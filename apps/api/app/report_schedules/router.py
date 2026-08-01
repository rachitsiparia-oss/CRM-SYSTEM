"""Scheduled report API — GROWTH_AND_INTELLIGENCE.md section 13.19. The
manual `/run-now` endpoint is the deterministic engine's entry point until
Phase 15 wires live cron dispatch (CLAUDE.md section 9's "engine, not
scheduler" split)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import ScheduledReport, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.report_schedules import service
from app.report_schedules.errors import ReportScheduleError
from app.report_schedules.schemas import (
    ReportDeliveryAttemptOut,
    ScheduledReportCreateIn,
    ScheduledReportOut,
    ScheduledReportRecipientCreateIn,
    ScheduledReportRecipientOut,
    SetEnabledIn,
)

router = APIRouter(prefix="/api/v1/report-schedules", tags=["report-schedules"])


async def _get_or_404(session: AsyncSession, scheduled_report_id: uuid.UUID) -> ScheduledReport:
    scheduled = await service.get_scheduled_report(session, scheduled_report_id)
    if scheduled is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Scheduled report not found.")
    return scheduled


@router.get("")
async def list_scheduled_reports(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("reports.schedule")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ScheduledReportOut]:
    rows, total = await service.list_scheduled_reports(session, page=page, page_size=page_size)
    return PaginatedResponse(
        data=[ScheduledReportOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scheduled_report(
    payload: ScheduledReportCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.schedule")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ScheduledReportOut]:
    scheduled = await service.create_scheduled_report(session, actor=actor, payload=payload)
    return DataResponse(
        data=ScheduledReportOut.model_validate(scheduled), meta=request_meta(request)
    )


@router.get("/{scheduled_report_id}")
async def get_scheduled_report(
    scheduled_report_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("reports.schedule")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ScheduledReportOut]:
    scheduled = await _get_or_404(session, scheduled_report_id)
    return DataResponse(
        data=ScheduledReportOut.model_validate(scheduled), meta=request_meta(request)
    )


@router.patch("/{scheduled_report_id}/enabled")
async def set_enabled(
    scheduled_report_id: uuid.UUID,
    payload: SetEnabledIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.schedule")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ScheduledReportOut]:
    scheduled = await _get_or_404(session, scheduled_report_id)
    scheduled = await service.set_enabled(
        session, scheduled_report=scheduled, actor=actor, is_enabled=payload.is_enabled
    )
    return DataResponse(
        data=ScheduledReportOut.model_validate(scheduled), meta=request_meta(request)
    )


@router.get("/{scheduled_report_id}/recipients")
async def list_recipients(
    scheduled_report_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("reports.schedule")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ScheduledReportRecipientOut]]:
    await _get_or_404(session, scheduled_report_id)
    rows = await service.list_recipients(session, scheduled_report_id)
    return DataResponse(
        data=[ScheduledReportRecipientOut.model_validate(r) for r in rows],
        meta=request_meta(request),
    )


@router.post("/{scheduled_report_id}/recipients", status_code=status.HTTP_201_CREATED)
async def add_recipient(
    scheduled_report_id: uuid.UUID,
    payload: ScheduledReportRecipientCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("reports.schedule.manage_recipients")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ScheduledReportRecipientOut]:
    scheduled = await _get_or_404(session, scheduled_report_id)
    recipient = await service.add_recipient(session, scheduled_report=scheduled, payload=payload)
    return DataResponse(
        data=ScheduledReportRecipientOut.model_validate(recipient), meta=request_meta(request)
    )


@router.post("/{scheduled_report_id}/run-now")
async def run_scheduled_report_now(
    scheduled_report_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("reports.schedule")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ReportDeliveryAttemptOut]]:
    scheduled = await _get_or_404(session, scheduled_report_id)
    try:
        attempts = await service.execute_due_occurrence(session, scheduled)
    except ReportScheduleError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=[ReportDeliveryAttemptOut.model_validate(a) for a in attempts],
        meta=request_meta(request),
    )


@router.get("/{scheduled_report_id}/delivery-attempts")
async def list_delivery_attempts(
    scheduled_report_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("reports.delivery.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReportDeliveryAttemptOut]:
    await _get_or_404(session, scheduled_report_id)
    rows, total = await service.list_delivery_attempts(
        session, scheduled_report_id=scheduled_report_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=[ReportDeliveryAttemptOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )
