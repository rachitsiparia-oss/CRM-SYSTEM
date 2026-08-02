import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import DataResponse, request_meta
from app.db.models import StaffUser
from app.db.session import get_db
from app.feature_flags import service
from app.feature_flags.errors import FeatureFlagError
from app.feature_flags.schemas import FeatureFlagCreateIn, FeatureFlagOut, SetFlagEnabledIn
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/feature-flags", tags=["feature-flags"])


@router.get("")
async def list_flags(
    request: Request,
    _actor: StaffUser = Depends(require_permission("settings.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[FeatureFlagOut]]:
    rows = await service.list_flags(session)
    return DataResponse(
        data=[FeatureFlagOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_flag(
    payload: FeatureFlagCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FeatureFlagOut]:
    try:
        flag = await service.create_flag(
            session,
            actor=actor,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            is_enabled=payload.is_enabled,
        )
    except FeatureFlagError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=FeatureFlagOut.model_validate(flag), meta=request_meta(request))


@router.patch("/{flag_id}/enabled")
async def set_flag_enabled(
    flag_id: uuid.UUID,
    payload: SetFlagEnabledIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FeatureFlagOut]:
    try:
        flag = await service.get_flag(session, flag_id)
        flag = await service.set_flag_enabled(
            session, flag=flag, actor=actor, is_enabled=payload.is_enabled
        )
    except FeatureFlagError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=FeatureFlagOut.model_validate(flag), meta=request_meta(request))
