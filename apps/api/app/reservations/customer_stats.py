"""Customer-360 reservation statistics — this phase's own instruction:
"show reservation history, visit frequency, no-show count, cancellation
count, average party size, preferred area/table/time, last visit, lifetime
visits. Future Loyalty integration must consume these values."

Computed via database-side aggregation over `reservations` at read time
(CLAUDE.md section 5.3) rather than stored as new `Customer` columns —
Phase 5's shipped, tested `Customer` schema stays untouched, and the
numbers are always exactly consistent with the reservation history itself.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Reservation, ReservationTableAssignment
from app.reservations.schemas import CustomerReservationStatsOut


async def get_customer_reservation_stats(
    session: AsyncSession, customer_id: uuid.UUID
) -> CustomerReservationStatsOut:
    completed = Reservation.status == "completed"

    counts_stmt = select(
        func.count().filter(completed),
        func.count().filter(Reservation.status == "no_show"),
        func.count().filter(
            Reservation.status.in_(("cancelled_by_customer", "cancelled_by_restaurant"))
        ),
        func.avg(Reservation.party_size).filter(completed),
        func.max(Reservation.completed_at).filter(completed),
    ).where(Reservation.customer_id == customer_id)
    row = (await session.execute(counts_stmt)).one()
    lifetime_visit_count, no_show_count, cancellation_count, average_party_size, last_visit_at = row

    preferred_area_stmt = (
        select(Reservation.dining_area_id, func.count().label("visit_count"))
        .where(
            Reservation.customer_id == customer_id,
            completed,
            Reservation.dining_area_id.isnot(None),
        )
        .group_by(Reservation.dining_area_id)
        .order_by(func.count().desc())
        .limit(1)
    )
    preferred_dining_area_id = await session.scalar(preferred_area_stmt)

    preferred_time_stmt = (
        select(Reservation.start_time, func.count().label("visit_count"))
        .where(Reservation.customer_id == customer_id, completed)
        .group_by(Reservation.start_time)
        .order_by(func.count().desc())
        .limit(1)
    )
    preferred_start_time = await session.scalar(preferred_time_stmt)

    preferred_table_stmt = (
        select(ReservationTableAssignment.restaurant_table_id, func.count().label("visit_count"))
        .join(Reservation, Reservation.id == ReservationTableAssignment.reservation_id)
        .where(Reservation.customer_id == customer_id, completed)
        .group_by(ReservationTableAssignment.restaurant_table_id)
        .order_by(func.count().desc())
        .limit(1)
    )
    preferred_table_id = await session.scalar(preferred_table_stmt)

    return CustomerReservationStatsOut(
        lifetime_visit_count=lifetime_visit_count,
        no_show_count=no_show_count,
        cancellation_count=cancellation_count,
        average_party_size=float(average_party_size) if average_party_size is not None else None,
        last_visit_at=last_visit_at,
        preferred_dining_area_id=preferred_dining_area_id,
        preferred_table_id=preferred_table_id,
        preferred_start_time=preferred_start_time,
    )
