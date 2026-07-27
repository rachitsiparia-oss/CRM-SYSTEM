"""Walk-in guest creation — this phase's own instruction: "create a
reservation from walk-in; reuse existing customer if found, otherwise create
automatically using the existing customer service." Kept as its own module
rather than folded into app.reservations.service since it composes across
two domains (reservations and customers) the way app.leads.service composes
with app.customers.service for lead conversion.
"""

import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.customers.schemas import CustomerCreateIn
from app.customers.service import create_customer, find_duplicate_customers
from app.db.models import (
    Customer,
    DiningArea,
    Reservation,
    ReservationStatusHistory,
    ReservationTimeline,
    StaffUser,
)
from app.outbox.service import record_domain_event
from app.reservations.schemas import WalkInCreateIn
from app.reservations.service import generate_reservation_number, get_large_party_threshold

# CLAUDE.md section 7: timestamps are stored in UTC, but a walk-in's
# reservation_date/start_time are the restaurant's own local wall-clock
# "right now" — the same rationale app.orders.service._RESTAURANT_TIMEZONE
# already established for "today".
_RESTAURANT_TIMEZONE = ZoneInfo("Asia/Kolkata")


async def _find_or_create_customer(
    session: AsyncSession, *, actor: StaffUser, payload: WalkInCreateIn, request: Request | None
) -> Customer | None:
    if payload.phone_e164 is None and payload.email is None:
        return None

    duplicates = await find_duplicate_customers(
        session, phone=payload.phone_e164, email=payload.email
    )
    if duplicates:
        return duplicates[0][0]

    return await create_customer(
        session,
        actor=actor,
        payload=CustomerCreateIn(
            display_name=payload.guest_name,
            primary_phone_e164=payload.phone_e164,
            primary_email=payload.email,
            acquisition_source="walk_in",
        ),
        request=request,
    )


async def create_walk_in(
    session: AsyncSession, *, actor: StaffUser, payload: WalkInCreateIn, request: Request | None
) -> Reservation:
    if payload.dining_area_id is not None:
        dining_area = await session.get(DiningArea, payload.dining_area_id)
        if dining_area is None or dining_area.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dining area not found."
            )

    large_party_threshold = await get_large_party_threshold(session)
    if payload.party_size > large_party_threshold:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Parties larger than {large_party_threshold} guests are handled as an "
                "event or bulk lead, not a standard walk-in."
            ),
        )

    customer = await _find_or_create_customer(
        session, actor=actor, payload=payload, request=request
    )

    now_utc = datetime.now(UTC)
    now_local = now_utc.astimezone(_RESTAURANT_TIMEZONE)

    reservation = Reservation(
        id=uuid.uuid4(),
        reservation_number=generate_reservation_number(),
        customer_id=customer.id if customer is not None else None,
        guest_name=payload.guest_name,
        phone_e164=payload.phone_e164,
        email=payload.email,
        party_size=payload.party_size,
        reservation_date=now_local.date(),
        start_time=now_local.time().replace(microsecond=0),
        dining_area_id=payload.dining_area_id,
        status="arrived",
        source="walk_in",
        is_walk_in=True,
        special_requests=payload.special_requests,
        approved_by=actor.id,
        approved_at=now_utc,
        arrived_at=now_utc,
        created_by=actor.id,
    )
    session.add(reservation)
    await session.flush()

    session.add(
        ReservationStatusHistory(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            previous_status=None,
            new_status="arrived",
            actor_id=actor.id,
            reason="Walk-in.",
        )
    )
    session.add(
        ReservationTimeline(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_type="created",
            summary=f"Walk-in {reservation.reservation_number} created and seated on arrival.",
            performed_by=actor.id,
            occurred_at=now_utc,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation.walk_in_created",
        target_type="reservation",
        target_id=reservation.id,
        request=request,
        safe_metadata={"reservation_number": reservation.reservation_number},
    )
    await record_domain_event(
        session,
        event_type="reservation.created",
        aggregate_type="reservation",
        aggregate_id=reservation.id,
        payload={
            "reservation_id": str(reservation.id),
            "reservation_number": reservation.reservation_number,
            "is_walk_in": True,
        },
    )
    await session.flush()
    return reservation
