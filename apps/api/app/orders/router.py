import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.customers.schemas import CustomerListItemOut
from app.db.models import (
    Customer,
    Order,
    OrderNote,
    OrderPayment,
    OrderStatusHistory,
    OrderTimeline,
    StaffUser,
)
from app.db.session import get_db
from app.inventory import order_integration as inventory_order_integration
from app.orders import service
from app.orders.schemas import (
    OrderAssignIn,
    OrderCreateIn,
    OrderDashboardStatsOut,
    OrderListItemOut,
    OrderNoteIn,
    OrderNoteOut,
    OrderOut,
    OrderPaymentCreateIn,
    OrderPaymentOut,
    OrderPaymentUpdateIn,
    OrderStatusHistoryOut,
    OrderTimelineOut,
    OrderTransitionIn,
    OrderUpdateIn,
)
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

_SORT_COLUMNS = {
    "newest": (Order.created_at, True),
    "oldest": (Order.created_at, False),
    "highest_amount": (Order.grand_total_minor, True),
    "lowest_amount": (Order.grand_total_minor, False),
    "completion_time": (Order.estimated_completion_time, False),
}


async def _get_order_or_404(session: AsyncSession, order_id: uuid.UUID) -> Order:
    order = await service.get_order(session, order_id)
    if order is None or order.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


@router.get("")
async def list_orders(
    request: Request,
    _actor: StaffUser = Depends(require_permission("orders.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
    order_status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    order_type: str | None = Query(default=None),
    payment_status: str | None = Query(default=None),
    assigned_staff_id: uuid.UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    min_amount_minor: int | None = Query(default=None, ge=0),
    max_amount_minor: int | None = Query(default=None, ge=0),
    sort: str = Query(default="newest"),
) -> PaginatedResponse[OrderListItemOut]:
    if sort not in _SORT_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort option."
        )

    stmt = select(Order).where(Order.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(Order).where(Order.deleted_at.is_(None))

    if search:
        pattern = f"%{search}%"
        clause = or_(
            Order.order_number.ilike(pattern),
            Order.internal_notes.ilike(pattern),
            Order.customer_notes.ilike(pattern),
        )
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if order_status:
        stmt = stmt.where(Order.status == order_status)
        count_stmt = count_stmt.where(Order.status == order_status)
    if source:
        stmt = stmt.where(Order.source == source)
        count_stmt = count_stmt.where(Order.source == source)
    if order_type:
        stmt = stmt.where(Order.order_type == order_type)
        count_stmt = count_stmt.where(Order.order_type == order_type)
    if payment_status:
        stmt = stmt.where(Order.payment_status == payment_status)
        count_stmt = count_stmt.where(Order.payment_status == payment_status)
    if assigned_staff_id:
        stmt = stmt.where(Order.assigned_staff_id == assigned_staff_id)
        count_stmt = count_stmt.where(Order.assigned_staff_id == assigned_staff_id)
    if date_from:
        stmt = stmt.where(Order.created_at >= date_from)
        count_stmt = count_stmt.where(Order.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Order.created_at <= date_to)
        count_stmt = count_stmt.where(Order.created_at <= date_to)
    if min_amount_minor is not None:
        stmt = stmt.where(Order.grand_total_minor >= min_amount_minor)
        count_stmt = count_stmt.where(Order.grand_total_minor >= min_amount_minor)
    if max_amount_minor is not None:
        stmt = stmt.where(Order.grand_total_minor <= max_amount_minor)
        count_stmt = count_stmt.where(Order.grand_total_minor <= max_amount_minor)

    total = await session.scalar(count_stmt) or 0
    column, descending = _SORT_COLUMNS[sort]
    stmt = stmt.order_by(column.desc() if descending else column.asc())
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [OrderListItemOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    _actor: StaffUser = Depends(require_permission("orders.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderDashboardStatsOut]:
    stats = await service.get_dashboard_stats(session)
    return DataResponse(data=stats, meta=request_meta(request))


@router.get("/search-customers")
async def search_order_customers(
    request: Request,
    _actor: StaffUser = Depends(require_permission("orders.create")),
    session: AsyncSession = Depends(get_db),
    q: str = Query(min_length=1, max_length=200),
) -> DataResponse[list[CustomerListItemOut]]:
    pattern = f"%{q}%"
    stmt = (
        select(Customer)
        .where(
            Customer.deleted_at.is_(None),
            or_(
                Customer.display_name.ilike(pattern),
                Customer.customer_number.ilike(pattern),
                Customer.primary_phone_e164.ilike(pattern),
            ),
        )
        .limit(20)
    )
    rows = (await session.scalars(stmt)).all()
    data = [CustomerListItemOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(
    request: Request,
    payload: OrderCreateIn,
    actor: StaffUser = Depends(require_permission("orders.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderOut]:
    order = await service.create_order(session, actor=actor, payload=payload, request=request)
    out = await service.build_order_out(session, order)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/{order_id}")
async def get_order(
    request: Request,
    order_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("orders.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderOut]:
    order = await _get_order_or_404(session, order_id)
    out = await service.build_order_out(session, order)
    return DataResponse(data=out, meta=request_meta(request))


@router.patch("/{order_id}")
async def update_order(
    request: Request,
    order_id: uuid.UUID,
    payload: OrderUpdateIn,
    actor: StaffUser = Depends(require_permission("orders.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderOut]:
    order = await _get_order_or_404(session, order_id)
    order = await service.update_order(
        session, actor=actor, order=order, payload=payload, request=request
    )
    out = await service.build_order_out(session, order)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/{order_id}/transition")
async def transition_order(
    request: Request,
    order_id: uuid.UUID,
    payload: OrderTransitionIn,
    actor: StaffUser = Depends(require_permission("orders.transition")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderOut]:
    order = await _get_order_or_404(session, order_id)
    # Runs the Phase 8 inventory side effect (reserve/consume/release)
    # around the unmodified Phase 7 state machine — see
    # app.inventory.order_integration's module docstring for the lifecycle.
    await inventory_order_integration.transition_order_with_inventory(
        session,
        actor=actor,
        order=order,
        new_status=payload.new_status,
        reason=payload.reason,
        request=request,
    )
    out = await service.build_order_out(session, order)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/{order_id}/assign")
async def assign_order(
    request: Request,
    order_id: uuid.UUID,
    payload: OrderAssignIn,
    actor: StaffUser = Depends(require_permission("orders.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderOut]:
    order = await _get_order_or_404(session, order_id)
    await service.assign_order(
        session,
        actor=actor,
        order=order,
        assigned_staff_id=payload.assigned_staff_id,
        request=request,
    )
    out = await service.build_order_out(session, order)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/{order_id}/timeline")
async def get_order_timeline(
    request: Request,
    order_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("orders.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
) -> PaginatedResponse[OrderTimelineOut]:
    await _get_order_or_404(session, order_id)
    stmt = (
        select(OrderTimeline)
        .where(OrderTimeline.order_id == order_id)
        .order_by(OrderTimeline.occurred_at.desc())
    )
    count_stmt = (
        select(func.count()).select_from(OrderTimeline).where(OrderTimeline.order_id == order_id)
    )
    total = await session.scalar(count_stmt) or 0
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [OrderTimelineOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/{order_id}/status-history")
async def get_order_status_history(
    request: Request,
    order_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("orders.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[OrderStatusHistoryOut]]:
    await _get_order_or_404(session, order_id)
    rows = (
        await session.scalars(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.created_at.desc())
        )
    ).all()
    data = [OrderStatusHistoryOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.get("/{order_id}/payments")
async def list_order_payments(
    request: Request,
    order_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("orders.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[OrderPaymentOut]]:
    await _get_order_or_404(session, order_id)
    rows = (
        await session.scalars(
            select(OrderPayment)
            .where(OrderPayment.order_id == order_id)
            .order_by(OrderPayment.recorded_at.desc())
        )
    ).all()
    data = [OrderPaymentOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/{order_id}/payments", status_code=status.HTTP_201_CREATED)
async def add_order_payment(
    request: Request,
    order_id: uuid.UUID,
    payload: OrderPaymentCreateIn,
    actor: StaffUser = Depends(require_permission("orders.payments.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderPaymentOut]:
    order = await _get_order_or_404(session, order_id)
    payment = await service.add_payment(
        session, actor=actor, order=order, payload=payload, request=request
    )
    return DataResponse(data=OrderPaymentOut.model_validate(payment), meta=request_meta(request))


async def _get_payment_or_404(
    session: AsyncSession, order_id: uuid.UUID, payment_id: uuid.UUID
) -> OrderPayment:
    payment = await session.scalar(
        select(OrderPayment).where(OrderPayment.id == payment_id, OrderPayment.order_id == order_id)
    )
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    return payment


@router.patch("/{order_id}/payments/{payment_id}")
async def update_order_payment(
    request: Request,
    order_id: uuid.UUID,
    payment_id: uuid.UUID,
    payload: OrderPaymentUpdateIn,
    actor: StaffUser = Depends(require_permission("orders.payments.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderPaymentOut]:
    order = await _get_order_or_404(session, order_id)
    payment = await _get_payment_or_404(session, order_id, payment_id)
    payment = await service.update_payment_status(
        session,
        actor=actor,
        order=order,
        payment=payment,
        new_status=payload.status,
        request=request,
    )
    return DataResponse(data=OrderPaymentOut.model_validate(payment), meta=request_meta(request))


@router.get("/{order_id}/notes")
async def list_order_notes(
    request: Request,
    order_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("orders.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[OrderNoteOut]]:
    await _get_order_or_404(session, order_id)
    rows = (
        await session.scalars(
            select(OrderNote)
            .where(OrderNote.order_id == order_id, OrderNote.deleted_at.is_(None))
            .order_by(OrderNote.created_at.desc())
        )
    ).all()
    data = [OrderNoteOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/{order_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_order_note(
    request: Request,
    order_id: uuid.UUID,
    payload: OrderNoteIn,
    actor: StaffUser = Depends(require_permission("orders.notes.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[OrderNoteOut]:
    order = await _get_order_or_404(session, order_id)
    note = await service.add_note(
        session, actor=actor, order=order, payload=payload, request=request
    )
    return DataResponse(data=OrderNoteOut.model_validate(note), meta=request_meta(request))
