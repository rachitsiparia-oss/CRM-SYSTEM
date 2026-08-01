"""Forecast API — GROWTH_AND_INTELLIGENCE.md section 15. `/run` is the
deterministic engine's manual trigger until Phase 15 wires a schedule."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import ForecastDefinition, StaffUser
from app.db.session import get_db
from app.forecasts import service
from app.forecasts.errors import ForecastError
from app.forecasts.schemas import (
    ForecastDefinitionCreateIn,
    ForecastDefinitionOut,
    ForecastSnapshotOut,
)
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/forecasts", tags=["forecasts"])


async def _get_definition_or_404(
    session: AsyncSession, definition_id: uuid.UUID
) -> ForecastDefinition:
    definition = await service.get_forecast_definition(session, definition_id)
    if definition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Forecast definition not found.")
    return definition


@router.get("/definitions")
async def list_forecast_definitions(
    request: Request,
    is_active: bool | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("forecasts.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ForecastDefinitionOut]]:
    rows = await service.list_forecast_definitions(session, is_active=is_active)
    return DataResponse(
        data=[ForecastDefinitionOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/definitions", status_code=status.HTTP_201_CREATED)
async def create_forecast_definition(
    payload: ForecastDefinitionCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("forecasts.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ForecastDefinitionOut]:
    try:
        definition = await service.create_forecast_definition(session, actor=actor, payload=payload)
    except ForecastError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=ForecastDefinitionOut.model_validate(definition), meta=request_meta(request)
    )


@router.post("/definitions/{definition_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_forecast(
    definition_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("forecasts.run")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ForecastSnapshotOut]:
    definition = await _get_definition_or_404(session, definition_id)
    snapshot = await service.run_forecast(session, definition)
    return DataResponse(
        data=ForecastSnapshotOut.model_validate(snapshot), meta=request_meta(request)
    )


@router.get("/definitions/{definition_id}/snapshots")
async def list_forecast_snapshots(
    definition_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("forecasts.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ForecastSnapshotOut]:
    await _get_definition_or_404(session, definition_id)
    rows, total = await service.list_forecast_snapshots(
        session, forecast_definition_id=definition_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=[ForecastSnapshotOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )
