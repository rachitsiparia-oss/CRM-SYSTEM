import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import DataResponse, request_meta
from app.db.models import Integration, StaffUser
from app.db.session import get_db
from app.integrations import service
from app.integrations.errors import IntegrationError
from app.integrations.health import run_health_checks
from app.integrations.schemas import HealthCheckSummaryOut, IntegrationOut
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


async def _get_or_404(session: AsyncSession, integration_id: uuid.UUID) -> Integration:
    try:
        return await service.get_integration(session, integration_id)
    except IntegrationError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc


@router.get("")
async def list_integrations(
    request: Request,
    category: str | None = Query(default=None),
    health_state: str | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("settings.integrations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[IntegrationOut]]:
    rows = await service.list_integrations(session, category=category, health_state=health_state)
    return DataResponse(
        data=[IntegrationOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.get("/{integration_id}")
async def get_integration(
    integration_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("settings.integrations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[IntegrationOut]:
    integration = await _get_or_404(session, integration_id)
    return DataResponse(data=IntegrationOut.model_validate(integration), meta=request_meta(request))


@router.post("/{integration_id}/pause")
async def pause_integration(
    integration_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("settings.integrations.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[IntegrationOut]:
    integration = await _get_or_404(session, integration_id)
    integration = await service.pause_integration(session, integration=integration, actor=actor)
    return DataResponse(data=IntegrationOut.model_validate(integration), meta=request_meta(request))


@router.post("/{integration_id}/resume")
async def resume_integration(
    integration_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("settings.integrations.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[IntegrationOut]:
    integration = await _get_or_404(session, integration_id)
    integration = await service.resume_integration(session, integration=integration, actor=actor)
    return DataResponse(data=IntegrationOut.model_validate(integration), meta=request_meta(request))


@router.post("/{integration_id}/disable")
async def disable_integration(
    integration_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("settings.integrations.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[IntegrationOut]:
    integration = await _get_or_404(session, integration_id)
    integration = await service.disable_integration(session, integration=integration, actor=actor)
    return DataResponse(data=IntegrationOut.model_validate(integration), meta=request_meta(request))


@router.post("/run-health-checks")
async def run_health_checks_endpoint(
    request: Request,
    _actor: StaffUser = Depends(require_permission("settings.integrations.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[HealthCheckSummaryOut]:
    counts = await run_health_checks(session)
    return DataResponse(
        data=HealthCheckSummaryOut(**counts),
        meta=request_meta(request),
    )
