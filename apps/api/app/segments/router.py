import uuid

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import Segment, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.segments import membership, service
from app.segments.errors import SegmentError
from app.segments.schemas import (
    MembershipAddIn,
    MembershipOut,
    MembershipRemoveIn,
    SegmentCreateIn,
    SegmentOut,
    SegmentPreviewOut,
    SegmentRefreshOut,
    SegmentTransitionIn,
    SegmentUpdateIn,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/segments", tags=["segments"])


async def _get_segment_or_404(session: AsyncSession, segment_id: uuid.UUID) -> Segment:
    segment = await service.get_segment(session, segment_id)
    if segment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Segment not found.")
    return segment


@router.get("")
async def list_segments(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    segment_type: str | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("segments.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SegmentOut]:
    rows, total = await service.list_segments(
        session, page=page, page_size=page_size, status=status_filter, segment_type=segment_type
    )
    return PaginatedResponse(
        data=[SegmentOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_segment(
    payload: SegmentCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("segments.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SegmentOut]:
    try:
        segment = await service.create_segment(session, actor=actor, payload=payload)
    except SegmentError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=SegmentOut.model_validate(segment), meta=request_meta(request))


@router.get("/{segment_id}")
async def get_segment(
    segment_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("segments.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SegmentOut]:
    segment = await _get_segment_or_404(session, segment_id)
    return DataResponse(data=SegmentOut.model_validate(segment), meta=request_meta(request))


@router.patch("/{segment_id}")
async def update_segment(
    segment_id: uuid.UUID,
    payload: SegmentUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("segments.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SegmentOut]:
    segment = await _get_segment_or_404(session, segment_id)
    try:
        segment = await service.update_segment(
            session, actor=actor, segment=segment, payload=payload
        )
    except SegmentError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=SegmentOut.model_validate(segment), meta=request_meta(request))


@router.post("/{segment_id}/transition")
async def transition_segment(
    segment_id: uuid.UUID,
    payload: SegmentTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("segments.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SegmentOut]:
    segment = await _get_segment_or_404(session, segment_id)
    try:
        segment = await service.transition_segment(
            session, actor=actor, segment=segment, target_status=payload.target_status
        )
    except SegmentError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=SegmentOut.model_validate(segment), meta=request_meta(request))


@router.get("/{segment_id}/members")
async def list_members(
    segment_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("segments.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[uuid.UUID]:
    await _get_segment_or_404(session, segment_id)
    member_ids, total = await membership.list_members(
        session, segment_id=segment_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=member_ids,
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/{segment_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    segment_id: uuid.UUID,
    payload: MembershipAddIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("segments.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[MembershipOut]:
    segment = await _get_segment_or_404(session, segment_id)
    try:
        row = await membership.add_static_member(
            session,
            segment=segment,
            customer_id=payload.customer_id,
            actor=actor,
            reason=payload.reason,
        )
    except SegmentError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=MembershipOut.model_validate(row), meta=request_meta(request))


@router.post("/{segment_id}/members/remove", status_code=status.HTTP_201_CREATED)
async def remove_member(
    segment_id: uuid.UUID,
    payload: MembershipRemoveIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("segments.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[MembershipOut]:
    segment = await _get_segment_or_404(session, segment_id)
    try:
        row = await membership.remove_static_member(
            session,
            segment=segment,
            customer_id=payload.customer_id,
            actor=actor,
            reason=payload.reason,
        )
    except SegmentError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=MembershipOut.model_validate(row), meta=request_meta(request))


@router.post("/{segment_id}/refresh")
async def refresh_segment(
    segment_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("segments.refresh")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SegmentRefreshOut]:
    segment = await _get_segment_or_404(session, segment_id)
    try:
        computed_count = await membership.refresh(session, segment=segment)
    except SegmentError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=SegmentRefreshOut(
            segment_id=segment.id,
            computed_count=computed_count,
            refreshed_at=segment.last_refreshed_at,  # type: ignore[arg-type]
        ),
        meta=request_meta(request),
    )


@router.get("/{segment_id}/preview")
async def preview_segment(
    segment_id: uuid.UUID,
    request: Request,
    customer_id: uuid.UUID = Query(...),
    _actor: StaffUser = Depends(require_permission("segments.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SegmentPreviewOut]:
    segment = await _get_segment_or_404(session, segment_id)
    try:
        result = await membership.evaluate_for_customer(
            session, segment=segment, customer_id=customer_id
        )
    except SegmentError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=SegmentPreviewOut(
            eligible=result.eligible,
            matched_facts=result.matched_facts,
            failed_facts=result.failed_facts,
            unknown_facts=result.unknown_facts,
        ),
        meta=request_meta(request),
    )
