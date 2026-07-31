import uuid

from app.achievements import awards, service
from app.achievements.errors import AchievementError
from app.achievements.schemas import (
    AchievementCreateIn,
    AchievementOut,
    AchievementUpdateIn,
    AwardOut,
    EvaluateAwardIn,
    ReverseAwardIn,
)
from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import Achievement, CustomerAchievementAward, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/achievements", tags=["achievements"])


async def _get_achievement_or_404(session: AsyncSession, achievement_id: uuid.UUID) -> Achievement:
    achievement = await service.get_achievement(session, achievement_id)
    if achievement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Achievement not found.")
    return achievement


async def _get_award_or_404(session: AsyncSession, award_id: uuid.UUID) -> CustomerAchievementAward:
    award = await awards.get_award(session, award_id)
    if award is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Achievement award not found.")
    return award


@router.get("")
async def list_achievements(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    is_active: bool | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("achievements.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AchievementOut]:
    rows, total = await service.list_achievements(
        session, page=page, page_size=page_size, is_active=is_active
    )
    return PaginatedResponse(
        data=[AchievementOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_achievement(
    payload: AchievementCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("achievements.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AchievementOut]:
    try:
        achievement = await service.create_achievement(session, actor=actor, payload=payload)
    except AchievementError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=AchievementOut.model_validate(achievement), meta=request_meta(request))


@router.get("/{achievement_id}")
async def get_achievement(
    achievement_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("achievements.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AchievementOut]:
    achievement = await _get_achievement_or_404(session, achievement_id)
    return DataResponse(data=AchievementOut.model_validate(achievement), meta=request_meta(request))


@router.patch("/{achievement_id}")
async def update_achievement(
    achievement_id: uuid.UUID,
    payload: AchievementUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("achievements.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AchievementOut]:
    achievement = await _get_achievement_or_404(session, achievement_id)
    achievement = await service.update_achievement(
        session, actor=actor, achievement=achievement, payload=payload
    )
    return DataResponse(data=AchievementOut.model_validate(achievement), meta=request_meta(request))


@router.post("/evaluate", status_code=status.HTTP_201_CREATED)
async def evaluate_and_award(
    payload: EvaluateAwardIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("achievements.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AwardOut]:
    achievement = await _get_achievement_or_404(session, payload.achievement_id)
    try:
        award = await awards.evaluate_and_award(
            session,
            actor=actor,
            achievement=achievement,
            customer_id=payload.customer_id,
            source_event_type=payload.source_event_type,
            source_event_key=payload.source_event_key,
        )
    except AchievementError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=AwardOut.model_validate(award), meta=request_meta(request))


@router.get("/awards/{award_id}")
async def get_award(
    award_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("achievements.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AwardOut]:
    award = await _get_award_or_404(session, award_id)
    return DataResponse(data=AwardOut.model_validate(award), meta=request_meta(request))


@router.post("/awards/{award_id}/reverse")
async def reverse_award(
    award_id: uuid.UUID,
    payload: ReverseAwardIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("achievements.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AwardOut]:
    award = await _get_award_or_404(session, award_id)
    achievement = await _get_achievement_or_404(session, award.achievement_id)
    try:
        award = await awards.reverse_award(
            session, actor=actor, award=award, achievement=achievement, reason=payload.reason
        )
    except AchievementError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=AwardOut.model_validate(award), meta=request_meta(request))
