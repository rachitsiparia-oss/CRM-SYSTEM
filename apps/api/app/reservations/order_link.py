"""Reservation-to-order linkage — this phase's own instruction: "reservation
can create order; order linked back to reservation ... no duplicated data."
Deliberately thin: creating the order itself stays entirely inside
app.orders.service (order items, pricing, and taxes are that module's own
domain), so this only records/clears the `Reservation.order_id` pointer
once an order already exists.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import Order, Reservation, ReservationTimeline, StaffUser


async def link_order(
    session: AsyncSession,
    *,
    actor: StaffUser,
    reservation: Reservation,
    order_id: uuid.UUID,
    request: Request | None,
) -> Reservation:
    if reservation.order_id == order_id:
        return reservation
    if reservation.order_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reservation is already linked to an order.",
        )

    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    reservation.order_id = order_id
    reservation.version += 1
    reservation.updated_by = actor.id
    session.add(
        ReservationTimeline(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_type="edited",
            summary=f"Linked to order {order.order_number}.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation.order_linked",
        target_type="reservation",
        target_id=reservation.id,
        request=request,
        safe_metadata={"order_id": str(order_id)},
    )
    return reservation


async def unlink_order(
    session: AsyncSession, *, actor: StaffUser, reservation: Reservation, request: Request | None
) -> Reservation:
    if reservation.order_id is None:
        return reservation

    previous_order_id = reservation.order_id
    reservation.order_id = None
    reservation.version += 1
    reservation.updated_by = actor.id
    session.add(
        ReservationTimeline(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_type="edited",
            summary="Order unlinked.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation.order_unlinked",
        target_type="reservation",
        target_id=reservation.id,
        request=request,
        safe_metadata={"order_id": str(previous_order_id)},
    )
    return reservation
