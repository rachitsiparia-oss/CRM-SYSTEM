import uuid

from app.commercial_risk import service
from app.commercial_risk.errors import CommercialRiskError
from app.commercial_risk.schemas import FlagOut, ReviewFlagIn
from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import CommercialRiskFlag, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/commercial-risk", tags=["commercial-risk"])


async def _get_flag_or_404(session: AsyncSession, flag_id: uuid.UUID) -> CommercialRiskFlag:
    flag = await service.get_flag(session, flag_id)
    if flag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Commercial-risk flag not found.")
    return flag


@router.get("/flags")
async def list_flags(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    flag_type: str | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("commercial_risk.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[FlagOut]:
    rows, total = await service.list_flags(
        session,
        page=page,
        page_size=page_size,
        status=status_filter,
        flag_type=flag_type,
        customer_id=customer_id,
    )
    return PaginatedResponse(
        data=[FlagOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/flags/{flag_id}")
async def get_flag(
    flag_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("commercial_risk.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FlagOut]:
    flag = await _get_flag_or_404(session, flag_id)
    return DataResponse(data=FlagOut.model_validate(flag), meta=request_meta(request))


@router.post("/flags/{flag_id}/review")
async def review_flag(
    flag_id: uuid.UUID,
    payload: ReviewFlagIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("commercial_risk.review")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FlagOut]:
    flag = await _get_flag_or_404(session, flag_id)
    try:
        flag = await service.review_flag(
            session,
            actor=actor,
            flag=flag,
            target_status=payload.target_status,
            resolution_note=payload.resolution_note,
        )
    except CommercialRiskError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=FlagOut.model_validate(flag), meta=request_meta(request))
