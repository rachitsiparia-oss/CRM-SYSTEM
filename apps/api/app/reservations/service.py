"""Reservation business logic — kept out of the router for the same reason
as app.orders.service (state-machine behavior needs to be unit-testable
without an HTTP client).
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    Customer,
    DiningArea,
    Reservation,
    ReservationNote,
    ReservationPolicies,
    ReservationStatusHistory,
    ReservationTimeline,
    StaffUser,
)
from app.outbox.service import record_domain_event
from app.permissions.service import has_permission
from app.reservations.availability import find_available_tables, is_within_operating_hours
from app.reservations.schemas import (
    ReservationCreateIn,
    ReservationNoteIn,
    ReservationUpdateIn,
)
from app.reservations.states import is_transition_allowed

# Statuses reached only through this phase's own dedicated entry points
# (approve_reservation/reject_reservation once app.reservations.availability
# lands in task #105) never through the generic transition endpoint —
# mirrors how app.orders.transition_order individually permission-gates
# `cancelled`/`completed` rather than trusting the caller.
_TERMINAL_STATUSES = frozenset(
    {
        "completed",
        "no_show",
        "cancelled_by_customer",
        "cancelled_by_restaurant",
        "rejected",
        "expired",
    }
)


def generate_reservation_number() -> str:
    return f"RES-{uuid.uuid4().hex[:8].upper()}"


async def get_reservation(session: AsyncSession, reservation_id: uuid.UUID) -> Reservation | None:
    return await session.get(Reservation, reservation_id)


# Matches ReservationPolicies.large_party_threshold's own column default —
# used only if the singleton settings row has not been seeded yet.
_DEFAULT_LARGE_PARTY_THRESHOLD = 18


async def get_large_party_threshold(session: AsyncSession) -> int:
    policies = await session.scalar(select(ReservationPolicies).limit(1))
    if policies is None:
        return _DEFAULT_LARGE_PARTY_THRESHOLD
    return policies.large_party_threshold


async def create_reservation(
    session: AsyncSession,
    *,
    actor: StaffUser,
    payload: ReservationCreateIn,
    request: Request | None,
) -> Reservation:
    existing = await session.scalar(
        select(Reservation).where(Reservation.idempotency_key == payload.idempotency_key)
    )
    if existing is not None:
        return existing

    if payload.customer_id is not None:
        customer = await session.get(Customer, payload.customer_id)
        if customer is None or customer.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    if payload.dining_area_id is not None:
        dining_area = await session.get(DiningArea, payload.dining_area_id)
        if dining_area is None or dining_area.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dining area not found."
            )

    # PROJECT_PLAN.md section 11.2: "Groups above 18 guests are handled as
    # event or bulk leads" — not automatically redirected (that decision
    # belongs to a human), just refused here so staff route it through the
    # leads workflow instead of a standard reservation.
    large_party_threshold = await get_large_party_threshold(session)
    if payload.party_size > large_party_threshold:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Parties larger than {large_party_threshold} guests are handled as an "
                "event or bulk lead, not a standard reservation."
            ),
        )

    reservation = Reservation(
        id=uuid.uuid4(),
        reservation_number=generate_reservation_number(),
        customer_id=payload.customer_id,
        guest_name=payload.guest_name,
        phone_e164=payload.phone_e164,
        email=payload.email,
        party_size=payload.party_size,
        reservation_date=payload.reservation_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        dining_area_id=payload.dining_area_id,
        status="requested",
        source=payload.source,
        is_walk_in=False,
        special_requests=payload.special_requests,
        deposit_required=payload.deposit_required,
        deposit_amount_minor=payload.deposit_amount_minor,
        idempotency_key=payload.idempotency_key,
        created_by=actor.id,
    )
    session.add(reservation)
    await session.flush()

    now = datetime.now(UTC)
    session.add(
        ReservationStatusHistory(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            previous_status=None,
            new_status="requested",
            actor_id=actor.id,
        )
    )
    session.add(
        ReservationTimeline(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_type="created",
            summary=(
                f"Reservation {reservation.reservation_number} requested via {reservation.source}."
            ),
            performed_by=actor.id,
            occurred_at=now,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation.created",
        target_type="reservation",
        target_id=reservation.id,
        request=request,
        safe_metadata={
            "reservation_number": reservation.reservation_number,
            "source": reservation.source,
        },
    )
    await record_domain_event(
        session,
        event_type="reservation.created",
        aggregate_type="reservation",
        aggregate_id=reservation.id,
        payload={
            "reservation_id": str(reservation.id),
            "reservation_number": reservation.reservation_number,
        },
    )
    await session.flush()
    return reservation


async def update_reservation(
    session: AsyncSession,
    *,
    actor: StaffUser,
    reservation: Reservation,
    payload: ReservationUpdateIn,
    request: Request | None,
) -> Reservation:
    if reservation.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservations in '{reservation.status}' status cannot be edited.",
        )
    if payload.expected_version is not None and payload.expected_version != reservation.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This reservation was updated by someone else. Reload and try again.",
        )

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = {field: getattr(reservation, field) for field in updates}
    for field, value in updates.items():
        setattr(reservation, field, value)

    if updates:
        reservation.version += 1
        reservation.updated_by = actor.id
        session.add(
            ReservationTimeline(
                id=uuid.uuid4(),
                reservation_id=reservation.id,
                event_type="edited",
                summary="Reservation details updated.",
                performed_by=actor.id,
                occurred_at=datetime.now(UTC),
            )
        )
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="reservation.updated",
            target_type="reservation",
            target_id=reservation.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return reservation


# Maps a target status to the ReservationTimeline event_type recorded for
# it — mirrors app.orders.service.transition_order's event_type branch.
# Anything not individually named here falls back to `status_changed`
# (see ReservationTimeline's own module docstring for why).
_TRANSITION_EVENT_TYPES: dict[str, str] = {
    "confirmed": "confirmed",
    "arrived": "checked_in",
    "no_show": "no_show",
    "completed": "completed",
    "cancelled_by_customer": "cancelled",
    "cancelled_by_restaurant": "cancelled",
}

# Individually-permission-gated targets, the same treatment
# app.orders.states gives `cancelled`/`completed` — every other allowed
# transition only needs the base `reservations.transition` grant.
_GATED_TRANSITIONS: dict[str, str] = {
    "cancelled_by_customer": "reservations.cancel",
    "cancelled_by_restaurant": "reservations.cancel",
    "completed": "reservations.complete",
    "approved": "reservations.approve",
    "rejected": "reservations.approve",
}


async def transition_reservation(
    session: AsyncSession,
    *,
    actor: StaffUser,
    reservation: Reservation,
    new_status: str,
    reason: str | None,
    request: Request | None,
) -> None:
    if not is_transition_allowed(reservation.status, new_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move a reservation from '{reservation.status}' to '{new_status}'.",
        )
    required_permission = _GATED_TRANSITIONS.get(new_status)
    if required_permission is not None and not await has_permission(
        session, actor.id, required_permission
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to move a reservation to '{new_status}'.",
        )

    previous_status = reservation.status
    reservation.status = new_status
    reservation.updated_by = actor.id
    reservation.version += 1

    now = datetime.now(UTC)
    if new_status == "approved":
        reservation.approved_by = actor.id
        reservation.approved_at = now
    elif new_status == "rejected":
        reservation.rejected_by = actor.id
        reservation.rejected_at = now
        reservation.rejection_reason = reason
    elif new_status == "arrived":
        reservation.arrived_at = now
    elif new_status == "seated":
        reservation.seated_at = now
    elif new_status == "completed":
        reservation.completed_at = now
    elif new_status == "no_show":
        reservation.no_show_at = now
    elif new_status in ("cancelled_by_customer", "cancelled_by_restaurant"):
        reservation.cancelled_at = now
        reservation.cancellation_source = (
            "customer" if new_status == "cancelled_by_customer" else "restaurant"
        )
        reservation.cancellation_reason = reason

    session.add(
        ReservationStatusHistory(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            previous_status=previous_status,
            new_status=new_status,
            actor_id=actor.id,
            reason=reason,
        )
    )
    session.add(
        ReservationTimeline(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_type=_TRANSITION_EVENT_TYPES.get(new_status, "status_changed"),
            summary=f"Status changed from {previous_status} to {new_status}.",
            performed_by=actor.id,
            occurred_at=now,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation.status_changed",
        target_type="reservation",
        target_id=reservation.id,
        request=request,
        before_summary={"status": previous_status},
        after_summary={"status": new_status},
        safe_metadata={"reason": reason},
    )
    await record_domain_event(
        session,
        event_type="reservation.status_changed",
        aggregate_type="reservation",
        aggregate_id=reservation.id,
        payload={
            "reservation_id": str(reservation.id),
            "previous_status": previous_status,
            "new_status": new_status,
        },
    )


_APPROVAL_ELIGIBLE_STATUSES = frozenset({"pending_review", "needs_clarification"})


async def approve_reservation(
    session: AsyncSession, *, actor: StaffUser, reservation: Reservation, request: Request | None
) -> None:
    """PROJECT_PLAN.md section 11.2: "Approval checks capacity, time,
    seating zone, special requests, operating hours, and conflicts."
    Special requests are surfaced for the human reviewer to read, not
    machine-validated — only the deterministic checks (hours, capacity,
    conflicts) can safely block approval outright.
    """
    if reservation.status not in _APPROVAL_ELIGIBLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservations in '{reservation.status}' status are not awaiting approval.",
        )

    if not await is_within_operating_hours(
        session,
        target_date=reservation.reservation_date,
        start_time=reservation.start_time,
        end_time=reservation.end_time,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested time falls outside operating hours.",
        )

    available_tables = await find_available_tables(
        session,
        target_date=reservation.reservation_date,
        start_time=reservation.start_time,
        end_time=reservation.end_time,
        party_size=reservation.party_size,
        dining_area_id=reservation.dining_area_id,
        exclude_reservation_id=reservation.id,
    )
    if not available_tables:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No table is available for this party size, date, and time.",
        )

    await transition_reservation(
        session,
        actor=actor,
        reservation=reservation,
        new_status="approved",
        reason=None,
        request=request,
    )


async def reject_reservation(
    session: AsyncSession,
    *,
    actor: StaffUser,
    reservation: Reservation,
    reason: str,
    request: Request | None,
) -> None:
    if reservation.status not in _APPROVAL_ELIGIBLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservations in '{reservation.status}' status are not awaiting approval.",
        )
    await transition_reservation(
        session,
        actor=actor,
        reservation=reservation,
        new_status="rejected",
        reason=reason,
        request=request,
    )


async def add_note(
    session: AsyncSession,
    *,
    actor: StaffUser,
    reservation: Reservation,
    payload: ReservationNoteIn,
    request: Request | None,
) -> ReservationNote:
    note = ReservationNote(
        id=uuid.uuid4(),
        reservation_id=reservation.id,
        note_type=payload.note_type,
        content=payload.content,
        is_internal=payload.is_internal,
        created_by=actor.id,
    )
    session.add(note)
    await session.flush()
    session.add(
        ReservationTimeline(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_type="edited",
            summary="Note added.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation.note_added",
        target_type="reservation",
        target_id=reservation.id,
        request=request,
        safe_metadata={"note_type": payload.note_type},
    )
    return note
