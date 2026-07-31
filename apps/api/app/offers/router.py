import uuid

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import Coupon, Offer, OfferRedemption, StaffUser
from app.db.session import get_db
from app.offers import coupons as coupons_service
from app.offers import redemptions, service
from app.offers.errors import OfferError
from app.offers.schemas import (
    ConfirmRedemptionIn,
    CouponCreateIn,
    CouponOut,
    OfferCreateIn,
    OfferOut,
    OfferPreviewIn,
    OfferPreviewOut,
    OfferRedemptionOut,
    OfferTransitionIn,
    OfferUpdateIn,
    OfferVersionCreateIn,
    OfferVersionOut,
    RejectRedemptionIn,
    ReserveRedemptionIn,
    ReverseRedemptionIn,
)
from app.permissions.dependencies import require_permission
from app.permissions.service import has_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/offers", tags=["offers"])


async def _get_offer_or_404(session: AsyncSession, offer_id: uuid.UUID) -> Offer:
    offer = await service.get_offer(session, offer_id)
    if offer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Offer not found.")
    return offer


async def _get_redemption_or_404(
    session: AsyncSession, redemption_id: uuid.UUID
) -> OfferRedemption:
    redemption = await session.get(OfferRedemption, redemption_id)
    if redemption is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Offer redemption not found.")
    return redemption


@router.get("")
async def list_offers(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    offer_type: str | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("offers.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OfferOut]:
    rows, total = await service.list_offers(
        session, page=page, page_size=page_size, status=status_filter, offer_type=offer_type
    )
    return PaginatedResponse(
        data=[OfferOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_offer(
    payload: OfferCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferOut]:
    try:
        offer = await service.create_offer(session, actor=actor, payload=payload)
    except (OfferError, ValueError) as exc:
        detail = exc.message if isinstance(exc, OfferError) else str(exc)
        status_code = (
            exc.status_code if isinstance(exc, OfferError) else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code, detail=detail) from exc
    return DataResponse(data=OfferOut.model_validate(offer), meta=request_meta(request))


@router.get("/{offer_id}")
async def get_offer(
    offer_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("offers.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferOut]:
    offer = await _get_offer_or_404(session, offer_id)
    return DataResponse(data=OfferOut.model_validate(offer), meta=request_meta(request))


@router.patch("/{offer_id}")
async def update_offer(
    offer_id: uuid.UUID,
    payload: OfferUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferOut]:
    offer = await _get_offer_or_404(session, offer_id)
    offer = await service.update_offer(session, actor=actor, offer=offer, payload=payload)
    return DataResponse(data=OfferOut.model_validate(offer), meta=request_meta(request))


@router.post("/{offer_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_version(
    offer_id: uuid.UUID,
    payload: OfferVersionCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferVersionOut]:
    offer = await _get_offer_or_404(session, offer_id)
    try:
        version = await service.create_new_version(
            session, actor=actor, offer=offer, payload=payload
        )
    except (OfferError, ValueError) as exc:
        detail = exc.message if isinstance(exc, OfferError) else str(exc)
        status_code = (
            exc.status_code if isinstance(exc, OfferError) else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code, detail=detail) from exc
    return DataResponse(data=OfferVersionOut.model_validate(version), meta=request_meta(request))


@router.post("/{offer_id}/transition")
async def transition_offer(
    offer_id: uuid.UUID,
    payload: OfferTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferOut]:
    if payload.target_status == "approved" and not await has_permission(
        session, actor.id, "offers.approve"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="offers.approve permission required.")
    offer = await _get_offer_or_404(session, offer_id)
    try:
        offer = await service.transition_offer(
            session, actor=actor, offer=offer, target_status=payload.target_status
        )
    except OfferError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=OfferOut.model_validate(offer), meta=request_meta(request))


@router.get("/{offer_id}/coupons")
async def list_coupons(
    offer_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("offers.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[CouponOut]]:
    await _get_offer_or_404(session, offer_id)
    rows = await session.scalars(
        select(Coupon).where(Coupon.offer_id == offer_id).order_by(Coupon.created_at.desc())
    )
    return DataResponse(
        data=[CouponOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/{offer_id}/coupons", status_code=status.HTTP_201_CREATED)
async def create_coupon(
    offer_id: uuid.UUID,
    payload: CouponCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CouponOut]:
    offer = await _get_offer_or_404(session, offer_id)
    try:
        coupon = await coupons_service.create_coupon(
            session, offer=offer, payload=payload, actor=actor
        )
    except OfferError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=CouponOut.model_validate(coupon), meta=request_meta(request))


@router.post("/{offer_id}/preview")
async def preview_offer(
    offer_id: uuid.UUID,
    payload: OfferPreviewIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("offers.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferPreviewOut]:
    offer = await _get_offer_or_404(session, offer_id)
    version = await service.get_latest_version(session, offer)
    outcome = await redemptions.evaluate_offer(
        session,
        offer=offer,
        version=version,
        customer_id=payload.customer_id,
        coupon_code=payload.coupon_code,
        order_channel=payload.order_channel,
        order_type=payload.order_type,
        subtotal_minor=payload.subtotal_minor,
        product_ids=payload.product_ids,
        category_ids=payload.category_ids,
        eligible_amount_minor=payload.eligible_amount_minor,
    )
    return DataResponse(
        data=OfferPreviewOut(
            eligible=outcome.eligible,
            matched_facts=outcome.rule_result.matched_facts,
            failed_facts=outcome.rule_result.failed_facts,
            unknown_facts=outcome.rule_result.unknown_facts,
            discount_amount_minor=outcome.discount_amount_minor,
            reasons=outcome.reasons,
        ),
        meta=request_meta(request),
    )


@router.post("/redemptions/reserve", status_code=status.HTTP_201_CREATED)
async def reserve_redemption(
    payload: ReserveRedemptionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.redeem")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferRedemptionOut]:
    try:
        redemption = await redemptions.reserve(
            session,
            offer_id=payload.offer_id,
            customer_id=payload.customer_id,
            coupon_code=payload.coupon_code,
            order_id=payload.order_id,
            order_channel=payload.order_channel,
            order_type=payload.order_type,
            subtotal_minor=payload.subtotal_minor,
            product_ids=payload.product_ids,
            category_ids=payload.category_ids,
            eligible_amount_minor=payload.eligible_amount_minor,
            idempotency_key=payload.idempotency_key,
            actor=actor,
        )
    except OfferError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=OfferRedemptionOut.model_validate(redemption), meta=request_meta(request)
    )


@router.get("/redemptions/{redemption_id}")
async def get_redemption(
    redemption_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("offers.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferRedemptionOut]:
    redemption = await _get_redemption_or_404(session, redemption_id)
    return DataResponse(
        data=OfferRedemptionOut.model_validate(redemption), meta=request_meta(request)
    )


@router.post("/redemptions/{redemption_id}/confirm")
async def confirm_redemption(
    redemption_id: uuid.UUID,
    payload: ConfirmRedemptionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.redeem")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferRedemptionOut]:
    redemption = await _get_redemption_or_404(session, redemption_id)
    try:
        redemption = await redemptions.confirm(
            session, redemption=redemption, order_id=payload.order_id, actor=actor
        )
    except OfferError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=OfferRedemptionOut.model_validate(redemption), meta=request_meta(request)
    )


@router.post("/redemptions/{redemption_id}/reject")
async def reject_redemption(
    redemption_id: uuid.UUID,
    payload: RejectRedemptionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.redeem")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferRedemptionOut]:
    redemption = await _get_redemption_or_404(session, redemption_id)
    try:
        redemption = await redemptions.reject(
            session, redemption=redemption, reason=payload.reason, actor=actor
        )
    except OfferError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=OfferRedemptionOut.model_validate(redemption), meta=request_meta(request)
    )


@router.post("/redemptions/{redemption_id}/reverse")
async def reverse_redemption(
    redemption_id: uuid.UUID,
    payload: ReverseRedemptionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("offers.reverse")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OfferRedemptionOut]:
    redemption = await _get_redemption_or_404(session, redemption_id)
    try:
        redemption = await redemptions.reverse(
            session, redemption=redemption, reason=payload.reason, actor=actor
        )
    except OfferError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=OfferRedemptionOut.model_validate(redemption), meta=request_meta(request)
    )
