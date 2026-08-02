from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import DataResponse, request_meta
from app.db.models import StaffUser
from app.db.session import get_db
from app.operational_settings import service
from app.operational_settings.errors import OperationalSettingsError
from app.operational_settings.schemas import OperationalSettingsOut, OperationalSettingsUpdateIn
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/operational-settings", tags=["operational-settings"])


@router.get("")
async def get_operational_settings(
    request: Request,
    _actor: StaffUser = Depends(require_permission("settings.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OperationalSettingsOut]:
    try:
        settings = await service.get_operational_settings(session)
    except OperationalSettingsError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=OperationalSettingsOut.model_validate(settings), meta=request_meta(request)
    )


@router.patch("")
async def update_operational_settings(
    payload: OperationalSettingsUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OperationalSettingsOut]:
    try:
        settings = await service.get_operational_settings(session)
        settings = await service.update_operational_settings(
            session, settings=settings, actor=actor, **payload.model_dump(exclude_unset=True)
        )
    except OperationalSettingsError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=OperationalSettingsOut.model_validate(settings), meta=request_meta(request)
    )
