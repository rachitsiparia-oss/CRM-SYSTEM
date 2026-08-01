"""Feedback and review-request API — GROWTH_AND_INTELLIGENCE.md section 11.
Two resource families under one router: `/feedback` (entries, ratings,
tags, conversion) and `/review-requests` (outreach lifecycle)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import FeedbackEntry, ReviewRequest, StaffUser
from app.db.session import get_db
from app.feedback import analytics, review_requests, service
from app.feedback.errors import FeedbackError
from app.feedback.schemas import (
    ConvertToComplaintIn,
    FeedbackAnalyticsOut,
    FeedbackCreateIn,
    FeedbackOut,
    FeedbackStatusHistoryOut,
    FeedbackTransitionIn,
    FeedbackUpdateIn,
    RatingOut,
    ReviewRequestAnalyticsOut,
    ReviewRequestCompleteIn,
    ReviewRequestCreateIn,
    ReviewRequestOut,
    TagAssignIn,
)
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])
review_requests_router = APIRouter(prefix="/api/v1/review-requests", tags=["feedback"])


async def _get_feedback_or_404(session: AsyncSession, feedback_id: uuid.UUID) -> FeedbackEntry:
    row = await service.get_feedback(session, feedback_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feedback entry not found.")
    return row


async def _get_review_request_or_404(
    session: AsyncSession, review_request_id: uuid.UUID
) -> ReviewRequest:
    row = await review_requests.get_review_request(session, review_request_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Review request not found.")
    return row


# --- Feedback ----------------------------------------------------------------


@router.get("")
async def list_feedback(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    source: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    order_id: uuid.UUID | None = Query(default=None),
    reservation_id: uuid.UUID | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("feedback.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[FeedbackOut]:
    rows, total = await service.list_feedback(
        session,
        page=page,
        page_size=page_size,
        status=status_filter,
        source=source,
        sentiment=sentiment,
        customer_id=customer_id,
        order_id=order_id,
        reservation_id=reservation_id,
    )
    return PaginatedResponse(
        data=[FeedbackOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("feedback.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FeedbackOut]:
    feedback = await service.create_feedback(session, actor=actor, payload=payload)
    return DataResponse(data=FeedbackOut.model_validate(feedback), meta=request_meta(request))


@router.get("/analytics")
async def get_feedback_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("feedback.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FeedbackAnalyticsOut]:
    result = await analytics.get_feedback_analytics(session)
    return DataResponse(data=result, meta=request_meta(request))


@router.get("/customers/{customer_id}/history")
async def get_customer_feedback_history(
    customer_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("feedback.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[FeedbackOut]:
    rows, total = await service.customer_feedback_history(
        session, customer_id=customer_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=[FeedbackOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/{feedback_id}")
async def get_feedback(
    feedback_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("feedback.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FeedbackOut]:
    feedback = await _get_feedback_or_404(session, feedback_id)
    return DataResponse(data=FeedbackOut.model_validate(feedback), meta=request_meta(request))


@router.patch("/{feedback_id}")
async def update_feedback(
    feedback_id: uuid.UUID,
    payload: FeedbackUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("feedback.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FeedbackOut]:
    feedback = await _get_feedback_or_404(session, feedback_id)
    feedback = await service.update_feedback(
        session, actor=actor, feedback=feedback, payload=payload
    )
    return DataResponse(data=FeedbackOut.model_validate(feedback), meta=request_meta(request))


@router.post("/{feedback_id}/transition")
async def transition_feedback(
    feedback_id: uuid.UUID,
    payload: FeedbackTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("feedback.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FeedbackOut]:
    feedback = await _get_feedback_or_404(session, feedback_id)
    try:
        feedback = await service.transition_feedback(
            session,
            actor=actor,
            feedback=feedback,
            target_status=payload.target_status,
            reason=payload.reason,
        )
    except FeedbackError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=FeedbackOut.model_validate(feedback), meta=request_meta(request))


@router.post("/{feedback_id}/convert-to-complaint", status_code=status.HTTP_201_CREATED)
async def convert_feedback_to_complaint(
    feedback_id: uuid.UUID,
    payload: ConvertToComplaintIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("feedback.convert_to_complaint")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, uuid.UUID]]:
    feedback = await _get_feedback_or_404(session, feedback_id)
    try:
        complaint = await service.convert_to_complaint(
            session, actor=actor, feedback=feedback, payload=payload
        )
    except FeedbackError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data={"complaint_id": complaint.id}, meta=request_meta(request))


@router.post("/{feedback_id}/tags")
async def assign_feedback_tags(
    feedback_id: uuid.UUID,
    payload: TagAssignIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("feedback.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[FeedbackOut]:
    feedback = await _get_feedback_or_404(session, feedback_id)
    await service.assign_tags(session, actor=actor, feedback=feedback, tag_ids=payload.tag_ids)
    return DataResponse(data=FeedbackOut.model_validate(feedback), meta=request_meta(request))


@router.get("/{feedback_id}/ratings")
async def list_feedback_ratings(
    feedback_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("feedback.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[RatingOut]]:
    await _get_feedback_or_404(session, feedback_id)
    rows = await service.list_ratings(session, feedback_id)
    return DataResponse(
        data=[RatingOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.get("/{feedback_id}/status-history")
async def list_feedback_status_history(
    feedback_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("feedback.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[FeedbackStatusHistoryOut]]:
    await _get_feedback_or_404(session, feedback_id)
    rows = await service.list_status_history(session, feedback_id)
    return DataResponse(
        data=[FeedbackStatusHistoryOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


# --- Review requests -----------------------------------------------------


@review_requests_router.get("")
async def list_review_requests(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: uuid.UUID | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("feedback.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReviewRequestOut]:
    rows, total = await review_requests.list_review_requests(
        session, page=page, page_size=page_size, status=status_filter, customer_id=customer_id
    )
    return PaginatedResponse(
        data=[ReviewRequestOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@review_requests_router.post("", status_code=status.HTTP_201_CREATED)
async def create_review_request(
    payload: ReviewRequestCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("feedback.request_review")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReviewRequestOut]:
    try:
        review_request = await review_requests.create_review_request(
            session, actor=actor, payload=payload
        )
    except FeedbackError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=ReviewRequestOut.model_validate(review_request), meta=request_meta(request)
    )


@review_requests_router.get("/analytics")
async def get_review_request_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("feedback.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReviewRequestAnalyticsOut]:
    result = await analytics.get_review_request_analytics(session)
    return DataResponse(data=result, meta=request_meta(request))


@review_requests_router.post("/process-pending")
async def process_pending_review_requests(
    request: Request,
    _actor: StaffUser = Depends(require_permission("feedback.request_review")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, int]]:
    """The deterministic, idempotent engine entry point instruction section
    9's "engine, not scheduler" split leaves for Phase 15 to put on a
    recurring schedule — manually triggerable meanwhile."""
    processed = await review_requests.process_pending_review_requests(session)
    return DataResponse(data={"processed": len(processed)}, meta=request_meta(request))


@review_requests_router.get("/{review_request_id}")
async def get_review_request(
    review_request_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("feedback.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReviewRequestOut]:
    review_request = await _get_review_request_or_404(session, review_request_id)
    return DataResponse(
        data=ReviewRequestOut.model_validate(review_request), meta=request_meta(request)
    )


@review_requests_router.post("/{review_request_id}/complete")
async def complete_review_request(
    review_request_id: uuid.UUID,
    payload: ReviewRequestCompleteIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("feedback.request_review")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReviewRequestOut]:
    review_request = await _get_review_request_or_404(session, review_request_id)
    try:
        review_request = await review_requests.complete_review_request(
            session, actor=actor, review_request=review_request, payload=payload
        )
    except FeedbackError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=ReviewRequestOut.model_validate(review_request), meta=request_meta(request)
    )


@review_requests_router.post("/{review_request_id}/cancel")
async def cancel_review_request(
    review_request_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("feedback.request_review")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReviewRequestOut]:
    review_request = await _get_review_request_or_404(session, review_request_id)
    try:
        review_request = await review_requests.cancel_review_request(
            session, review_request=review_request
        )
    except FeedbackError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=ReviewRequestOut.model_validate(review_request), meta=request_meta(request)
    )
