import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import StaffUser
from app.db.session import get_db
from app.jobs import service
from app.jobs.catalog import SCHEDULED_JOB_CATALOG
from app.jobs.errors import JobError
from app.jobs.runner import cancel_job
from app.jobs.schemas import (
    JobRecordOut,
    QueueStatOut,
    SchedulerCatalogEntryOut,
    SchedulerStatusOut,
    SchedulerUpdateIn,
)
from app.operational_settings import service as operational_settings_service
from app.operational_settings.errors import OperationalSettingsError
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
scheduler_router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


@router.get("")
async def list_jobs(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    job_type: str | None = Query(default=None),
    queue_name: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("jobs.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[JobRecordOut]:
    rows, total = await service.list_job_records(
        session,
        status=status_filter,
        job_type=job_type,
        queue_name=queue_name,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        data=[JobRecordOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/queue-stats")
async def queue_stats(
    request: Request,
    _actor: StaffUser = Depends(require_permission("queues.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[QueueStatOut]]:
    stats = await service.get_queue_stats(session)
    return DataResponse(
        data=[QueueStatOut.model_validate(s) for s in stats], meta=request_meta(request)
    )


@router.get("/{job_id}")
async def get_job(
    job_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("jobs.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[JobRecordOut]:
    from app.db.models import JobRecord

    job = await session.get(JobRecord, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return DataResponse(data=JobRecordOut.model_validate(job), meta=request_meta(request))


@router.post("/{job_id}/cancel")
async def cancel_job_endpoint(
    job_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("jobs.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[JobRecordOut]:
    try:
        job = await cancel_job(session, job_id=job_id)
    except JobError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=JobRecordOut.model_validate(job), meta=request_meta(request))


@scheduler_router.get("")
async def get_scheduler_status(
    request: Request,
    _actor: StaffUser = Depends(require_permission("scheduler.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SchedulerStatusOut]:
    try:
        settings = await operational_settings_service.get_operational_settings(session)
    except OperationalSettingsError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=SchedulerStatusOut(
            scheduler_enabled=settings.scheduler_enabled,
            jobs=[SchedulerCatalogEntryOut(**entry._asdict()) for entry in SCHEDULED_JOB_CATALOG],
        ),
        meta=request_meta(request),
    )


@scheduler_router.patch("")
async def update_scheduler_status(
    payload: SchedulerUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("scheduler.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SchedulerStatusOut]:
    try:
        settings = await operational_settings_service.get_operational_settings(session)
        settings = await operational_settings_service.update_operational_settings(
            session, settings=settings, actor=actor, scheduler_enabled=payload.scheduler_enabled
        )
    except OperationalSettingsError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=SchedulerStatusOut(
            scheduler_enabled=settings.scheduler_enabled,
            jobs=[SchedulerCatalogEntryOut(**entry._asdict()) for entry in SCHEDULED_JOB_CATALOG],
        ),
        meta=request_meta(request),
    )
