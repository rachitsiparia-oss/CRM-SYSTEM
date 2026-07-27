"""The reservation assignment engine — this phase's own instruction:
"auto-assign best table considering guest count, existing reservations,
buffer time, area preference, VIP, wheelchair accessibility; manual
override; never overbook." Auto-assignment only ever suggests from the set
`app.reservations.availability.find_available_tables` already proved
conflict-free — it never bypasses that check, so "never overbook" holds for
both the automatic and manual path.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import Reservation, ReservationTableAssignment, ReservationTimeline, StaffUser
from app.reservations.availability import find_available_tables, is_table_available
from app.reservations.tables import get_table, is_table_transition_allowed, transition_table_status

# A reservation can only hold a table once it has passed the human-approval
# gate (or is a walk-in, created already past it) — assigning a table to a
# still-`requested`/`pending_review` booking would reserve floor space for
# something that might yet be rejected.
_ASSIGNABLE_STATUSES = frozenset(
    {"approved", "confirmation_sending", "confirmed", "reminder_scheduled", "arrived", "seated"}
)


async def suggest_table(
    session: AsyncSession,
    *,
    reservation: Reservation,
    requires_wheelchair_accessible: bool = False,
) -> uuid.UUID | None:
    """Returns the best-fit available table id, or None if nothing qualifies
    in the guest's preferred dining area — callers should retry without an
    area preference before concluding no table exists at all.
    """
    candidates = await find_available_tables(
        session,
        target_date=reservation.reservation_date,
        start_time=reservation.start_time,
        end_time=reservation.end_time,
        party_size=reservation.party_size,
        dining_area_id=reservation.dining_area_id,
        exclude_reservation_id=reservation.id,
    )
    if requires_wheelchair_accessible:
        candidates = [t for t in candidates if t.is_wheelchair_accessible]
    if not candidates and reservation.dining_area_id is not None:
        candidates = await find_available_tables(
            session,
            target_date=reservation.reservation_date,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            party_size=reservation.party_size,
            dining_area_id=None,
            exclude_reservation_id=reservation.id,
        )
        if requires_wheelchair_accessible:
            candidates = [t for t in candidates if t.is_wheelchair_accessible]
    return candidates[0].id if candidates else None


async def assign_tables(
    session: AsyncSession,
    *,
    actor: StaffUser,
    reservation: Reservation,
    table_ids: list[uuid.UUID],
    request: Request | None,
) -> list[ReservationTableAssignment]:
    if reservation.status not in _ASSIGNABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservations in '{reservation.status}' status cannot be assigned a table.",
        )

    tables = []
    for table_id in table_ids:
        table = await get_table(session, table_id)
        if table is None or table.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Table {table_id} not found."
            )
        if not await is_table_available(
            session,
            table=table,
            target_date=reservation.reservation_date,
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            party_size=reservation.party_size,
            exclude_reservation_id=reservation.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Table {table.table_number} is not available for this reservation.",
            )
        tables.append(table)

    existing_assignments = (
        await session.scalars(
            select(ReservationTableAssignment).where(
                ReservationTableAssignment.reservation_id == reservation.id,
                ReservationTableAssignment.unassigned_at.is_(None),
            )
        )
    ).all()
    is_reassignment = bool(existing_assignments)
    now = datetime.now(UTC)
    for assignment in existing_assignments:
        assignment.unassigned_at = now

    new_assignments = []
    occupied_status = "occupied" if reservation.status in ("arrived", "seated") else "reserved"
    for table in tables:
        new_assignments.append(
            ReservationTableAssignment(
                id=uuid.uuid4(),
                reservation_id=reservation.id,
                restaurant_table_id=table.id,
                assigned_by=actor.id,
            )
        )
        if is_table_transition_allowed(table.status, occupied_status):
            await transition_table_status(
                session,
                actor=actor,
                table=table,
                new_status=occupied_status,
                reason=f"Assigned to reservation {reservation.reservation_number}.",
                request=request,
            )
    session.add_all(new_assignments)
    await session.flush()

    session.add(
        ReservationTimeline(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            event_type="moved" if is_reassignment else "assigned",
            summary=(
                f"Reassigned to table(s) {', '.join(t.table_number for t in tables)}."
                if is_reassignment
                else f"Assigned to table(s) {', '.join(t.table_number for t in tables)}."
            ),
            performed_by=actor.id,
            occurred_at=now,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation.tables_assigned",
        target_type="reservation",
        target_id=reservation.id,
        request=request,
        safe_metadata={"table_ids": [str(t.id) for t in tables]},
    )
    return new_assignments


async def unassign_tables(
    session: AsyncSession,
    *,
    actor: StaffUser,
    reservation: Reservation,
    release_tables: bool,
    request: Request | None,
) -> None:
    assignments = (
        await session.scalars(
            select(ReservationTableAssignment).where(
                ReservationTableAssignment.reservation_id == reservation.id,
                ReservationTableAssignment.unassigned_at.is_(None),
            )
        )
    ).all()
    if not assignments:
        return

    now = datetime.now(UTC)
    for assignment in assignments:
        assignment.unassigned_at = now
        if release_tables:
            table = await get_table(session, assignment.restaurant_table_id)
            if table is not None and is_table_transition_allowed(table.status, "available"):
                await transition_table_status(
                    session,
                    actor=actor,
                    table=table,
                    new_status="available",
                    reason=f"Released from reservation {reservation.reservation_number}.",
                    request=request,
                )

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="reservation.tables_unassigned",
        target_type="reservation",
        target_id=reservation.id,
        request=request,
        safe_metadata={"table_ids": [str(a.restaurant_table_id) for a in assignments]},
    )
