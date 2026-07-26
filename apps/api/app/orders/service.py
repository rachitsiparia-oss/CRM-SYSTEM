"""Order business logic — kept out of the router for the same reason as
app.leads.service and app.menu.service (state-machine and pricing behavior
needs to be unit-testable without an HTTP client). All monetary
calculations happen here, server-side, in integer minor units — client-
supplied totals are never trusted (CLAUDE.md section 7 and section 24).
"""

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    Customer,
    Lead,
    Modifier,
    Order,
    OrderAssignment,
    OrderCharge,
    OrderDiscount,
    OrderItem,
    OrderItemModifier,
    OrderNote,
    OrderPayment,
    OrderStatusHistory,
    OrderTax,
    OrderTimeline,
    Product,
    ProductVariant,
    StaffUser,
)
from app.orders.schemas import (
    OrderChargeOut,
    OrderCreateIn,
    OrderDashboardStatsOut,
    OrderDiscountIn,
    OrderDiscountOut,
    OrderItemCreateIn,
    OrderItemModifierOut,
    OrderItemOut,
    OrderNoteIn,
    OrderOut,
    OrderPaymentCreateIn,
    OrderStatusCountsOut,
    OrderTaxIn,
    OrderTaxOut,
    OrderUpdateIn,
    RecentOrderActivityOut,
)
from app.orders.states import is_transition_allowed
from app.outbox.service import record_domain_event
from app.permissions.service import has_permission

# This project has no ORM `relationship()` mappings anywhere (every existing
# module — customers, leads, menu — composes related rows via explicit
# queries instead); order detail composition follows the same convention
# rather than introducing the first one.

# CLAUDE.md section 7: "Store timestamps in UTC and convert for display
# using the configured restaurant timezone (Asia/Kolkata)." "Today" for the
# dashboard's own counters is computed in that timezone, not UTC midnight —
# a fast-food restaurant's business day starts at local midnight.
_RESTAURANT_TIMEZONE = ZoneInfo("Asia/Kolkata")


def generate_order_number() -> str:
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


async def get_order(session: AsyncSession, order_id: uuid.UUID) -> Order | None:
    return await session.get(Order, order_id)


async def build_order_out(session: AsyncSession, order: Order) -> OrderOut:
    items = (
        await session.scalars(
            select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.created_at)
        )
    ).all()
    item_ids = [item.id for item in items]
    modifiers_by_item: dict[uuid.UUID, list[OrderItemModifier]] = {
        item_id: [] for item_id in item_ids
    }
    if item_ids:
        modifiers = (
            await session.scalars(
                select(OrderItemModifier).where(OrderItemModifier.order_item_id.in_(item_ids))
            )
        ).all()
        for modifier_row in modifiers:
            modifiers_by_item[modifier_row.order_item_id].append(modifier_row)

    item_outs = [
        OrderItemOut.model_validate(item).model_copy(
            update={
                "modifiers": [
                    OrderItemModifierOut.model_validate(m) for m in modifiers_by_item[item.id]
                ]
            }
        )
        for item in items
    ]
    discounts = (
        await session.scalars(select(OrderDiscount).where(OrderDiscount.order_id == order.id))
    ).all()
    taxes = (await session.scalars(select(OrderTax).where(OrderTax.order_id == order.id))).all()
    charges = (
        await session.scalars(select(OrderCharge).where(OrderCharge.order_id == order.id))
    ).all()

    return OrderOut.model_validate(order).model_copy(
        update={
            "items": item_outs,
            "discounts": [OrderDiscountOut.model_validate(d) for d in discounts],
            "taxes": [OrderTaxOut.model_validate(t) for t in taxes],
            "charges": [OrderChargeOut.model_validate(c) for c in charges],
        }
    )


async def _validate_and_price_item(
    session: AsyncSession, item_in: OrderItemCreateIn
) -> tuple[OrderItem, list[OrderItemModifier]]:
    product = await session.get(Product, item_in.product_id)
    if product is None or product.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product {item_in.product_id} not found.",
        )

    variant: ProductVariant | None = None
    if item_in.variant_id is not None:
        variant = await session.get(ProductVariant, item_in.variant_id)
        if variant is None or variant.product_id != product.id or variant.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Variant does not belong to the selected product.",
            )

    unit_price_minor = variant.price_minor if variant is not None else product.base_price_minor

    modifier_rows: list[tuple[Modifier, int]] = []
    modifiers_total_per_unit = 0
    for mod_in in item_in.modifiers:
        modifier = await session.get(Modifier, mod_in.modifier_id)
        if modifier is None or modifier.deleted_at is not None or not modifier.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Modifier {mod_in.modifier_id} is not available.",
            )
        modifiers_total_per_unit += modifier.default_price_minor * mod_in.quantity
        modifier_rows.append((modifier, mod_in.quantity))

    final_price_minor = item_in.quantity * (unit_price_minor + modifiers_total_per_unit)

    order_item = OrderItem(
        id=uuid.uuid4(),
        product_id=product.id,
        variant_id=variant.id if variant is not None else None,
        product_name_snapshot=product.display_name or product.name,
        variant_name_snapshot=variant.name if variant is not None else None,
        product_code_snapshot=product.product_code,
        quantity=item_in.quantity,
        unit_price_minor=unit_price_minor,
        discount_minor=0,
        tax_minor=0,
        final_price_minor=final_price_minor,
        kitchen_note=item_in.kitchen_note,
        status="active",
    )
    item_modifiers = [
        OrderItemModifier(
            id=uuid.uuid4(),
            modifier_id=modifier.id,
            modifier_name_snapshot=modifier.name,
            price_minor_snapshot=modifier.default_price_minor,
            quantity=qty,
        )
        for modifier, qty in modifier_rows
    ]
    return order_item, item_modifiers


def _resolve_discount_amount(disc_in: OrderDiscountIn, subtotal_minor: int) -> int:
    if disc_in.amount_minor is not None:
        return disc_in.amount_minor
    if disc_in.percentage is not None:
        return round(subtotal_minor * disc_in.percentage / 100)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Each discount requires either amount_minor or percentage.",
    )


def _resolve_tax_amount(tax_in: OrderTaxIn, taxable_base_minor: int) -> int:
    if tax_in.amount_minor is not None:
        return tax_in.amount_minor
    if tax_in.rate_percentage is not None:
        return round(taxable_base_minor * tax_in.rate_percentage / 100)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Each tax line requires either amount_minor or rate_percentage.",
    )


async def create_order(
    session: AsyncSession, *, actor: StaffUser, payload: OrderCreateIn, request: Request | None
) -> Order:
    existing = await session.scalar(
        select(Order).where(Order.idempotency_key == payload.idempotency_key)
    )
    if existing is not None:
        return existing

    if payload.discounts and not await has_permission(
        session, actor.id, "orders.discount.override"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to apply order discounts.",
        )

    if payload.customer_id is not None:
        customer = await session.get(Customer, payload.customer_id)
        if customer is None or customer.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    if payload.lead_id is not None:
        lead = await session.get(Lead, payload.lead_id)
        if lead is None or lead.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    if payload.assigned_staff_id is not None:
        staff = await session.get(StaffUser, payload.assigned_staff_id)
        if staff is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assigned staff member not found."
            )

    order = Order(
        id=uuid.uuid4(),
        order_number=generate_order_number(),
        customer_id=payload.customer_id,
        lead_id=payload.lead_id,
        source=payload.source,
        order_type=payload.order_type,
        status="draft",
        payment_status="pending",
        assigned_staff_id=payload.assigned_staff_id,
        internal_notes=payload.internal_notes,
        customer_notes=payload.customer_notes,
        estimated_completion_time=payload.estimated_completion_time,
        idempotency_key=payload.idempotency_key,
        created_by=actor.id,
    )
    session.add(order)
    await session.flush()

    subtotal_minor = 0
    for item_in in payload.items:
        order_item, item_modifiers = await _validate_and_price_item(session, item_in)
        order_item.order_id = order.id
        order_item.created_by = actor.id
        session.add(order_item)
        await session.flush()
        for modifier_row in item_modifiers:
            modifier_row.order_item_id = order_item.id
            session.add(modifier_row)
        subtotal_minor += order_item.final_price_minor

    discount_total = 0
    for disc_in in payload.discounts:
        approver = await session.get(StaffUser, disc_in.approved_by)
        if approver is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="approved_by does not reference a valid staff member.",
            )
        amount = _resolve_discount_amount(disc_in, subtotal_minor)
        session.add(
            OrderDiscount(
                id=uuid.uuid4(),
                order_id=order.id,
                discount_type=disc_in.discount_type,
                amount_minor=amount,
                percentage=disc_in.percentage,
                reason=disc_in.reason,
                approved_by=disc_in.approved_by,
                created_by=actor.id,
            )
        )
        discount_total += amount

    taxable_base = max(subtotal_minor - discount_total, 0)
    tax_total = 0
    for tax_in in payload.taxes:
        amount = _resolve_tax_amount(tax_in, taxable_base)
        session.add(
            OrderTax(
                id=uuid.uuid4(),
                order_id=order.id,
                tax_name=tax_in.tax_name,
                rate_percentage=tax_in.rate_percentage,
                amount_minor=amount,
            )
        )
        tax_total += amount

    charges_total = 0
    for charge_in in payload.charges:
        session.add(
            OrderCharge(
                id=uuid.uuid4(),
                order_id=order.id,
                charge_type=charge_in.charge_type,
                amount_minor=charge_in.amount_minor,
            )
        )
        charges_total += charge_in.amount_minor

    order.subtotal_minor = subtotal_minor
    order.discount_minor = discount_total
    order.tax_minor = tax_total
    order.charges_minor = charges_total
    order.grand_total_minor = max(subtotal_minor - discount_total + tax_total + charges_total, 0)

    now = datetime.now(UTC)
    session.add(
        OrderStatusHistory(
            id=uuid.uuid4(),
            order_id=order.id,
            previous_status=None,
            new_status="draft",
            actor_id=actor.id,
        )
    )
    session.add(
        OrderTimeline(
            id=uuid.uuid4(),
            order_id=order.id,
            event_type="created",
            summary=f"Order {order.order_number} created via {order.source}.",
            performed_by=actor.id,
            occurred_at=now,
        )
    )
    if payload.assigned_staff_id is not None:
        session.add(
            OrderAssignment(
                id=uuid.uuid4(),
                order_id=order.id,
                staff_id=payload.assigned_staff_id,
                assigned_by=actor.id,
            )
        )
        session.add(
            OrderTimeline(
                id=uuid.uuid4(),
                order_id=order.id,
                event_type="assigned",
                summary="Order assigned at creation.",
                performed_by=actor.id,
                occurred_at=now,
            )
        )

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="order.created",
        target_type="order",
        target_id=order.id,
        request=request,
        safe_metadata={"order_number": order.order_number, "source": order.source},
    )
    await record_domain_event(
        session,
        event_type="order.created",
        aggregate_type="order",
        aggregate_id=order.id,
        payload={"order_id": str(order.id), "order_number": order.order_number},
    )
    await session.flush()
    return order


async def update_order(
    session: AsyncSession,
    *,
    actor: StaffUser,
    order: Order,
    payload: OrderUpdateIn,
    request: Request | None,
) -> Order:
    if order.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Orders in '{order.status}' status cannot be edited.",
        )
    if payload.expected_version is not None and payload.expected_version != order.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order was updated by someone else. Reload and try again.",
        )

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = {field: getattr(order, field) for field in updates}
    for field, value in updates.items():
        setattr(order, field, value)

    if updates:
        order.version += 1
        order.updated_by = actor.id
        session.add(
            OrderTimeline(
                id=uuid.uuid4(),
                order_id=order.id,
                event_type="manual_edit",
                summary="Order details updated.",
                performed_by=actor.id,
                occurred_at=datetime.now(UTC),
            )
        )
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="order.updated",
            target_type="order",
            target_id=order.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return order


async def transition_order(
    session: AsyncSession,
    *,
    actor: StaffUser,
    order: Order,
    new_status: str,
    reason: str | None,
    request: Request | None,
) -> None:
    if not is_transition_allowed(order.status, new_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move an order from '{order.status}' to '{new_status}'.",
        )
    if new_status == "cancelled" and not await has_permission(session, actor.id, "orders.cancel"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel orders.",
        )
    if new_status == "completed" and not await has_permission(session, actor.id, "orders.complete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to complete orders.",
        )

    previous_status = order.status
    order.status = new_status
    order.updated_by = actor.id
    order.version += 1

    now = datetime.now(UTC)
    session.add(
        OrderStatusHistory(
            id=uuid.uuid4(),
            order_id=order.id,
            previous_status=previous_status,
            new_status=new_status,
            actor_id=actor.id,
            reason=reason,
        )
    )
    event_type = (
        "cancelled"
        if new_status == "cancelled"
        else "completed"
        if new_status == "completed"
        else "status_changed"
    )
    session.add(
        OrderTimeline(
            id=uuid.uuid4(),
            order_id=order.id,
            event_type=event_type,
            summary=f"Status changed from {previous_status} to {new_status}.",
            performed_by=actor.id,
            occurred_at=now,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="order.status_changed",
        target_type="order",
        target_id=order.id,
        request=request,
        before_summary={"status": previous_status},
        after_summary={"status": new_status},
        safe_metadata={"reason": reason},
    )
    await record_domain_event(
        session,
        event_type="order.status_changed",
        aggregate_type="order",
        aggregate_id=order.id,
        payload={
            "order_id": str(order.id),
            "previous_status": previous_status,
            "new_status": new_status,
        },
    )


async def assign_order(
    session: AsyncSession,
    *,
    actor: StaffUser,
    order: Order,
    assigned_staff_id: uuid.UUID,
    request: Request | None,
) -> None:
    staff = await session.get(StaffUser, assigned_staff_id)
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")

    previous_id = order.assigned_staff_id
    now = datetime.now(UTC)
    open_assignment = await session.scalar(
        select(OrderAssignment).where(
            OrderAssignment.order_id == order.id, OrderAssignment.unassigned_at.is_(None)
        )
    )
    if open_assignment is not None:
        open_assignment.unassigned_at = now

    session.add(
        OrderAssignment(
            id=uuid.uuid4(),
            order_id=order.id,
            staff_id=assigned_staff_id,
            assigned_by=actor.id,
        )
    )
    order.assigned_staff_id = assigned_staff_id
    order.updated_by = actor.id
    order.version += 1
    session.add(
        OrderTimeline(
            id=uuid.uuid4(),
            order_id=order.id,
            event_type="assigned",
            summary=f"Order assigned to staff member {assigned_staff_id}.",
            performed_by=actor.id,
            occurred_at=now,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="order.assigned",
        target_type="order",
        target_id=order.id,
        request=request,
        before_summary={"assigned_staff_id": str(previous_id) if previous_id else None},
        after_summary={"assigned_staff_id": str(assigned_staff_id)},
    )


async def _recompute_payment_status(session: AsyncSession, order: Order) -> None:
    payments = (
        await session.scalars(select(OrderPayment).where(OrderPayment.order_id == order.id))
    ).all()
    paid_total = sum(p.amount_minor for p in payments if p.status == "paid")
    if any(p.status == "refunded" for p in payments):
        order.payment_status = "refunded"
    elif paid_total <= 0:
        order.payment_status = (
            "failed" if any(p.status == "failed" for p in payments) else "pending"
        )
    elif paid_total < order.grand_total_minor:
        order.payment_status = "partial"
    else:
        order.payment_status = "paid"


async def add_payment(
    session: AsyncSession,
    *,
    actor: StaffUser,
    order: Order,
    payload: OrderPaymentCreateIn,
    request: Request | None,
) -> OrderPayment:
    payment = OrderPayment(
        id=uuid.uuid4(),
        order_id=order.id,
        method=payload.method,
        status=payload.status,
        amount_minor=payload.amount_minor,
        reference=payload.reference,
        notes=payload.notes,
        recorded_by=actor.id,
    )
    session.add(payment)
    await session.flush()
    await _recompute_payment_status(session, order)
    session.add(
        OrderTimeline(
            id=uuid.uuid4(),
            order_id=order.id,
            event_type="payment_updated",
            summary=f"Payment of {payload.amount_minor} recorded via {payload.method}.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="order.payment_recorded",
        target_type="order",
        target_id=order.id,
        request=request,
        safe_metadata={
            "payment_id": str(payment.id),
            "method": payload.method,
            "amount_minor": payload.amount_minor,
        },
    )
    return payment


async def update_payment_status(
    session: AsyncSession,
    *,
    actor: StaffUser,
    order: Order,
    payment: OrderPayment,
    new_status: str,
    request: Request | None,
) -> OrderPayment:
    previous_status = payment.status
    payment.status = new_status
    payment.updated_by = actor.id
    payment.updated_at = datetime.now(UTC)
    await _recompute_payment_status(session, order)
    session.add(
        OrderTimeline(
            id=uuid.uuid4(),
            order_id=order.id,
            event_type="payment_updated",
            summary=f"Payment status changed from {previous_status} to {new_status}.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="order.payment_status_changed",
        target_type="order",
        target_id=order.id,
        request=request,
        before_summary={"status": previous_status},
        after_summary={"status": new_status},
        safe_metadata={"payment_id": str(payment.id)},
    )
    return payment


async def add_note(
    session: AsyncSession,
    *,
    actor: StaffUser,
    order: Order,
    payload: OrderNoteIn,
    request: Request | None,
) -> OrderNote:
    note = OrderNote(
        id=uuid.uuid4(),
        order_id=order.id,
        content=payload.content,
        is_internal=payload.is_internal,
        created_by=actor.id,
    )
    session.add(note)
    session.add(
        OrderTimeline(
            id=uuid.uuid4(),
            order_id=order.id,
            event_type="note_added",
            summary="Internal note added."
            if payload.is_internal
            else "Customer-facing note added.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="order.note_added",
        target_type="order",
        target_id=order.id,
        request=request,
        safe_metadata={"is_internal": payload.is_internal},
    )
    await session.flush()
    return note


async def get_dashboard_stats(session: AsyncSession) -> OrderDashboardStatsOut:
    """This phase's own instruction: "Orders Dashboard with real-data
    statistics... today's orders, pending/preparing/ready/completed/
    cancelled counts, revenue today, average order value, recent
    activity." Every number here is a database-side aggregate
    (CLAUDE.md section 5.3: "Use database-side aggregation for dashboard
    metrics") — never a full order list fetched and reduced client-side.
    """
    now_local = datetime.now(_RESTAURANT_TIMEZONE)
    start_of_day_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_day_utc = start_of_day_local.astimezone(UTC)
    end_of_day_utc = (start_of_day_local + timedelta(days=1)).astimezone(UTC)
    today_range = (Order.created_at >= start_of_day_utc, Order.created_at < end_of_day_utc)

    today_order_count = (
        await session.scalar(select(func.count()).select_from(Order).where(*today_range))
    ) or 0

    status_rows = await session.execute(
        select(Order.status, func.count()).where(*today_range).group_by(Order.status)
    )
    counts_by_status: dict[str, int] = {row[0]: row[1] for row in status_rows.all()}
    status_counts_today = OrderStatusCountsOut(
        pending_confirmation=counts_by_status.get("pending_confirmation", 0),
        preparing=counts_by_status.get("preparing", 0),
        ready=counts_by_status.get("ready", 0),
        completed=counts_by_status.get("completed", 0),
        cancelled=counts_by_status.get("cancelled", 0),
    )

    revenue_today_minor = (
        await session.scalar(
            select(func.coalesce(func.sum(Order.grand_total_minor), 0)).where(
                *today_range, Order.status == "completed"
            )
        )
    ) or 0
    completed_today_count = status_counts_today.completed
    average_order_value_minor = (
        revenue_today_minor // completed_today_count if completed_today_count > 0 else 0
    )

    recent_rows = (
        await session.execute(
            select(
                OrderTimeline.order_id,
                Order.order_number,
                OrderTimeline.event_type,
                OrderTimeline.summary,
                OrderTimeline.occurred_at,
            )
            .join(Order, Order.id == OrderTimeline.order_id)
            .order_by(OrderTimeline.occurred_at.desc())
            .limit(10)
        )
    ).all()
    recent_activity = [
        RecentOrderActivityOut(
            order_id=row.order_id,
            order_number=row.order_number,
            event_type=row.event_type,
            summary=row.summary,
            occurred_at=row.occurred_at,
        )
        for row in recent_rows
    ]

    return OrderDashboardStatsOut(
        today_order_count=today_order_count,
        status_counts_today=status_counts_today,
        revenue_today_minor=revenue_today_minor,
        average_order_value_minor=average_order_value_minor,
        recent_activity=recent_activity,
    )
