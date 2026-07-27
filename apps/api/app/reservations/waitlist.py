"""Waitlist business logic — this phase's own instruction: "priority,
arrival time, party size, estimated wait, notification-ready, manual/
automatic promotion, reason, history." Promotion here only records the
linkage to an already-created reservation; creating that reservation (a
walk-in via `app.reservations.walkin`, or an approved advance booking) is
the caller's job, keeping this module decoupled from how the seat was
actually produced.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import Reservation, ReservationTimeline, ReservationWaitlist, StaffUser
from app.reservations.schemas import WaitlistCreateIn

_OPEN_STATUSES = frozenset({"waiting", "notified"})


async def get_waitlist_entry(
    session: AsyncSession, entry_id: uuid.UUID
) -> ReservationWaitlist | None:
    return await session.get(ReservationWaitlist, entry_id)


async def add_to_waitlist(
    session: AsyncSession, *, actor: StaffUser, payload: WaitlistCreateIn, request: Request | None
) -> ReservationWaitlist:
    entry = ReservationWaitlist(
        id=uuid.uuid4(),
        customer_id=payload.customer_id,
        guest_name=payload.guest_name,
        phone_e164=payload.phone_e164,
        email=payload.email,
        party_size=payload.party_size,
        dining_area_id=payload.dining_area_id,
        priority=payload.priority,
        status="waiting",
        estimated_wait_minutes=payload.estimated_wait_minutes,
        notes=payload.notes,
        created_by=actor.id,
    )
    session.add(entry)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation_waitlist.created",
        target_type="reservation_waitlist",
        target_id=entry.id,
        request=request,
        safe_metadata={"party_size": entry.party_size},
    )
    return entry


async def notify_waitlist_entry(
    session: AsyncSession, *, actor: StaffUser, entry: ReservationWaitlist, request: Request | None
) -> None:
    if entry.status != "waiting":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waitlist entries in '{entry.status}' status cannot be notified.",
        )
    entry.status = "notified"
    entry.notified_at = datetime.now(UTC)
    entry.updated_by = actor.id
    entry.version += 1
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation_waitlist.notified",
        target_type="reservation_waitlist",
        target_id=entry.id,
        request=request,
    )


async def promote_waitlist_entry(
    session: AsyncSession,
    *,
    actor: StaffUser,
    entry: ReservationWaitlist,
    reservation: Reservation,
    request: Request | None,
) -> None:
    if entry.status not in _OPEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waitlist entries in '{entry.status}' status cannot be promoted.",
        )

    now = datetime.now(UTC)
    entry.status = "promoted"
    entry.promoted_reservation_id = reservation.id
    entry.resolved_at = now
    entry.updated_by = actor.id
    entry.version += 1

    session.add(
        ReservationTimeline(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_type="promoted",
            summary="Promoted from the waitlist.",
            performed_by=actor.id,
            occurred_at=now,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation_waitlist.promoted",
        target_type="reservation_waitlist",
        target_id=entry.id,
        request=request,
        safe_metadata={"reservation_id": str(reservation.id)},
    )


async def cancel_waitlist_entry(
    session: AsyncSession,
    *,
    actor: StaffUser,
    entry: ReservationWaitlist,
    reason: str | None,
    request: Request | None,
) -> None:
    if entry.status not in _OPEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waitlist entries in '{entry.status}' status cannot be cancelled.",
        )
    entry.status = "cancelled"
    entry.resolved_at = datetime.now(UTC)
    entry.updated_by = actor.id
    entry.version += 1
    if reason:
        entry.notes = f"{entry.notes}\n{reason}" if entry.notes else reason
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation_waitlist.cancelled",
        target_type="reservation_waitlist",
        target_id=entry.id,
        request=request,
        safe_metadata={"reason": reason},
    )


async def expire_waitlist_entry(
    session: AsyncSession, *, actor: StaffUser, entry: ReservationWaitlist, request: Request | None
) -> None:
    """Called by staff (or a future scheduled job — see this phase's
    "engine, not scheduler" convention, matched elsewhere in this phase)
    once an entry has outlived its own estimated wait without being
    promoted or cancelled."""
    if entry.status not in _OPEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Waitlist entries in '{entry.status}' status cannot expire.",
        )
    entry.status = "expired"
    entry.resolved_at = datetime.now(UTC)
    entry.updated_by = actor.id
    entry.version += 1
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation_waitlist.expired",
        target_type="reservation_waitlist",
        target_id=entry.id,
        request=request,
    )
