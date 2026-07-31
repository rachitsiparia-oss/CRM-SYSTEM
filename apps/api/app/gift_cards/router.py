import uuid

from app.audit.service import record_audit_event
from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import GiftCard, GiftCardLedgerEntry, StaffUser
from app.db.session import get_db
from app.gift_cards import analytics, redemption, security, service
from app.gift_cards.errors import GiftCardError
from app.gift_cards.schemas import (
    AdjustGiftCardIn,
    GiftCardAnalyticsOut,
    GiftCardOut,
    IssueGiftCardIn,
    IssueGiftCardOut,
    LedgerEntryOut,
    RedeemGiftCardIn,
    RevealCodeOut,
    ReverseEntryIn,
    StatusActionIn,
)
from app.permissions.dependencies import require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/gift-cards", tags=["gift-cards"])


def _to_out(card: GiftCard) -> GiftCardOut:
    return GiftCardOut(
        id=card.id,
        card_number=card.card_number,
        masked_display=security.masked_display(card.code_last4),
        purchaser_customer_id=card.purchaser_customer_id,
        purchaser_contact=card.purchaser_contact,
        recipient_customer_id=card.recipient_customer_id,
        recipient_name=card.recipient_name,
        recipient_contact=card.recipient_contact,
        initial_amount_minor=card.initial_amount_minor,
        current_balance_minor=card.current_balance_minor,
        status=card.status,  # type: ignore[arg-type]
        issued_at=card.issued_at,
        purchased_at=card.purchased_at,
        activated_at=card.activated_at,
        expires_at=card.expires_at,
        source_order_id=card.source_order_id,
        delivery_status=card.delivery_status,
        notes=card.notes,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


async def _get_card_or_404(session: AsyncSession, gift_card_id: uuid.UUID) -> GiftCard:
    card = await service.get_gift_card(session, gift_card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Gift card not found.")
    return card


async def _get_entry_or_404(session: AsyncSession, entry_id: uuid.UUID) -> GiftCardLedgerEntry:
    entry = await redemption.get_entry(session, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Gift card ledger entry not found.")
    return entry


@router.get("")
async def list_gift_cards(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: uuid.UUID | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("gift_cards.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[GiftCardOut]:
    rows, total = await service.list_gift_cards(
        session, page=page, page_size=page_size, status=status_filter, customer_id=customer_id
    )
    return PaginatedResponse(
        data=[_to_out(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def issue_gift_card(
    payload: IssueGiftCardIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.issue")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[IssueGiftCardOut]:
    try:
        card, code = await service.issue_card(session, actor=actor, payload=payload)
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=IssueGiftCardOut(gift_card=_to_out(card), code=security.format_code_display(code)),
        meta=request_meta(request),
    )


@router.get("/{gift_card_id}")
async def get_gift_card(
    gift_card_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("gift_cards.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[GiftCardOut]:
    card = await _get_card_or_404(session, gift_card_id)
    return DataResponse(data=_to_out(card), meta=request_meta(request))


@router.get("/{gift_card_id}/reveal")
async def reveal_gift_card(
    gift_card_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.reveal_sensitive")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RevealCodeOut]:
    card = await _get_card_or_404(session, gift_card_id)
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="gift_card.code_revealed",
        target_type="gift_card",
        target_id=card.id,
        safe_metadata={},
    )
    return DataResponse(
        data=RevealCodeOut(card_number=card.card_number, code_last4=card.code_last4),
        meta=request_meta(request),
    )


@router.post("/{gift_card_id}/activate")
async def activate_gift_card(
    gift_card_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.issue")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[GiftCardOut]:
    card = await _get_card_or_404(session, gift_card_id)
    try:
        card = await service.activate_card(session, actor=actor, card=card)
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=_to_out(card), meta=request_meta(request))


@router.post("/{gift_card_id}/suspend")
async def suspend_gift_card(
    gift_card_id: uuid.UUID,
    payload: StatusActionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[GiftCardOut]:
    card = await _get_card_or_404(session, gift_card_id)
    try:
        card = await service.suspend_card(session, actor=actor, card=card, reason=payload.reason)
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=_to_out(card), meta=request_meta(request))


@router.post("/{gift_card_id}/reinstate")
async def reinstate_gift_card(
    gift_card_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[GiftCardOut]:
    card = await _get_card_or_404(session, gift_card_id)
    try:
        card = await service.reinstate_card(session, actor=actor, card=card)
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=_to_out(card), meta=request_meta(request))


@router.post("/{gift_card_id}/cancel")
async def cancel_gift_card(
    gift_card_id: uuid.UUID,
    payload: StatusActionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[GiftCardOut]:
    card = await _get_card_or_404(session, gift_card_id)
    try:
        card = await service.cancel_card(session, actor=actor, card=card, reason=payload.reason)
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=_to_out(card), meta=request_meta(request))


@router.post("/{gift_card_id}/expire")
async def expire_gift_card(
    gift_card_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[GiftCardOut]:
    card = await _get_card_or_404(session, gift_card_id)
    try:
        card = await service.expire_card(session, actor=actor, card=card)
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=_to_out(card), meta=request_meta(request))


@router.post("/{gift_card_id}/adjust")
async def adjust_gift_card(
    gift_card_id: uuid.UUID,
    payload: AdjustGiftCardIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    card = await _get_card_or_404(session, gift_card_id)
    try:
        entry = await service.adjust_card(session, actor=actor, card=card, payload=payload)
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.get("/{gift_card_id}/ledger")
async def list_ledger(
    gift_card_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("gift_cards.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[LedgerEntryOut]:
    await _get_card_or_404(session, gift_card_id)
    total = await session.scalar(
        select(func.count())
        .select_from(GiftCardLedgerEntry)
        .where(GiftCardLedgerEntry.gift_card_id == gift_card_id)
    )
    rows = await session.scalars(
        select(GiftCardLedgerEntry)
        .where(GiftCardLedgerEntry.gift_card_id == gift_card_id)
        .order_by(GiftCardLedgerEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PaginatedResponse(
        data=[LedgerEntryOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total or 0),
        meta=request_meta(request),
    )


@router.post("/redeem", status_code=status.HTTP_201_CREATED)
async def redeem_gift_card(
    payload: RedeemGiftCardIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await redemption.redeem_by_code(
            session,
            actor=actor,
            code=payload.code,
            pin=payload.pin,
            amount_minor=payload.amount_minor,
            order_id=payload.order_id,
            idempotency_key=payload.idempotency_key,
        )
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/reverse", status_code=status.HTTP_201_CREATED)
async def reverse_redemption(
    payload: ReverseEntryIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("gift_cards.reverse")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    entry = await _get_entry_or_404(session, payload.entry_id)
    try:
        reversal = await redemption.reverse_redemption(
            session,
            actor=actor,
            entry=entry,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
        )
    except GiftCardError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(reversal), meta=request_meta(request))


@router.get("/analytics")
async def get_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("gift_cards.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[GiftCardAnalyticsOut]:
    result = await analytics.get_analytics(session)
    return DataResponse(data=result, meta=request_meta(request))
