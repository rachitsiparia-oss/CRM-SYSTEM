import uuid

from app.campaigns import audience, execution, service
from app.campaigns.errors import CampaignError
from app.campaigns.schemas import (
    BuildAudienceOut,
    CampaignAnalyticsOut,
    CampaignCreateIn,
    CampaignOut,
    CampaignRecipientOut,
    CampaignTransitionIn,
    CampaignUpdateIn,
    LaunchCampaignOut,
)
from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import Campaign, CampaignRecipient, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.permissions.service import has_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])

_TRANSITION_PERMISSION_OVERRIDES: dict[str, str] = {
    "scheduled": "campaigns.approve",
    "running": "campaigns.execute",
    "paused": "campaigns.cancel",
    "cancelled": "campaigns.cancel",
}


async def _get_campaign_or_404(session: AsyncSession, campaign_id: uuid.UUID) -> Campaign:
    campaign = await service.get_campaign(session, campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    return campaign


@router.get("")
async def list_campaigns(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    _actor: StaffUser = Depends(require_permission("campaigns.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CampaignOut]:
    rows, total = await service.list_campaigns(
        session, page=page, page_size=page_size, status=status_filter
    )
    return PaginatedResponse(
        data=[CampaignOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("campaigns.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CampaignOut]:
    try:
        campaign = await service.create_campaign(session, actor=actor, payload=payload)
    except CampaignError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=CampaignOut.model_validate(campaign), meta=request_meta(request))


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("campaigns.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CampaignOut]:
    campaign = await _get_campaign_or_404(session, campaign_id)
    return DataResponse(data=CampaignOut.model_validate(campaign), meta=request_meta(request))


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("campaigns.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CampaignOut]:
    campaign = await _get_campaign_or_404(session, campaign_id)
    try:
        campaign = await service.update_campaign(
            session, actor=actor, campaign=campaign, payload=payload
        )
    except CampaignError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=CampaignOut.model_validate(campaign), meta=request_meta(request))


@router.post("/{campaign_id}/transition")
async def transition_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("campaigns.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CampaignOut]:
    required = _TRANSITION_PERMISSION_OVERRIDES.get(payload.target_status)
    if required is not None and not await has_permission(session, actor.id, required):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"{required} permission required.")

    campaign = await _get_campaign_or_404(session, campaign_id)
    try:
        campaign = await service.transition_campaign(
            session,
            actor=actor,
            campaign=campaign,
            target_status=payload.target_status,
            reason=payload.reason,
        )
    except CampaignError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=CampaignOut.model_validate(campaign), meta=request_meta(request))


@router.post("/{campaign_id}/audience/build")
async def build_audience(
    campaign_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("campaigns.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[BuildAudienceOut]:
    campaign = await _get_campaign_or_404(session, campaign_id)
    try:
        estimated_size = await audience.build_audience(session, campaign=campaign)
    except CampaignError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=BuildAudienceOut(
            campaign_id=campaign.id,
            estimated_size=estimated_size,
            audience_snapshot_taken_at=campaign.audience_snapshot_taken_at,  # type: ignore[arg-type]
        ),
        meta=request_meta(request),
    )


@router.get("/{campaign_id}/recipients")
async def list_recipients(
    campaign_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    _actor: StaffUser = Depends(require_permission("campaigns.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CampaignRecipientOut]:
    await _get_campaign_or_404(session, campaign_id)
    query = select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_id)
    count_query = (
        select(func.count())
        .select_from(CampaignRecipient)
        .where(CampaignRecipient.campaign_id == campaign_id)
    )
    if status_filter is not None:
        query = query.where(CampaignRecipient.status == status_filter)
        count_query = count_query.where(CampaignRecipient.status == status_filter)

    total = await session.scalar(count_query)
    rows = await session.scalars(
        query.order_by(CampaignRecipient.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PaginatedResponse(
        data=[CampaignRecipientOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total or 0),
        meta=request_meta(request),
    )


@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("campaigns.execute")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LaunchCampaignOut]:
    campaign = await _get_campaign_or_404(session, campaign_id)
    try:
        queued, suppressed = await execution.launch(session, campaign=campaign, actor=actor)
    except CampaignError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=LaunchCampaignOut(
            campaign_id=campaign.id, queued_count=queued, suppressed_count=suppressed
        ),
        meta=request_meta(request),
    )


@router.post("/{campaign_id}/sync")
async def sync_campaign(
    campaign_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("campaigns.execute")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, int]]:
    campaign = await _get_campaign_or_404(session, campaign_id)
    updated = await execution.sync_recipient_statuses(session, campaign=campaign)
    return DataResponse(data={"updated": updated}, meta=request_meta(request))


@router.get("/{campaign_id}/analytics")
async def campaign_analytics(
    campaign_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("campaigns.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CampaignAnalyticsOut]:
    await _get_campaign_or_404(session, campaign_id)
    counts = await execution.get_analytics(session, campaign_id=campaign_id)
    return DataResponse(
        data=CampaignAnalyticsOut(campaign_id=campaign_id, **counts), meta=request_meta(request)
    )
