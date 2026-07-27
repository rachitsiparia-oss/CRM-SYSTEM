"""Reservation dashboard aggregation — this phase's own instruction:
"today's/upcoming/completed/cancelled/no-show/walk-in reservations,
occupancy, peak hours, average party size/duration, area/table utilization,
reservation conversion, capacity heatmaps." Every number here is computed
with database-side aggregation (CLAUDE.md section 5.2) for a single target
date — never a full-table scan into application memory.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Reservation, ReservationTableAssignment
from app.reservations.schemas import ReservationDashboardStatsOut

_UPCOMING_STATUSES = frozenset(
    {"approved", "confirmation_sending", "confirmed", "reminder_scheduled"}
)
_CANCELLED_STATUSES = frozenset({"cancelled_by_customer", "cancelled_by_restaurant"})
_CONVERSION_DENOMINATOR_STATUSES = frozenset({"completed", "no_show", *_CANCELLED_STATUSES})


async def get_reservation_dashboard_stats(
    session: AsyncSession, *, target_date: date
) -> ReservationDashboardStatsOut:
    for_date = Reservation.reservation_date == target_date
    completed = Reservation.status == "completed"

    counts_stmt = select(
        func.count(),
        func.count().filter(Reservation.status.in_(_UPCOMING_STATUSES)),
        func.count().filter(completed),
        func.count().filter(Reservation.status.in_(_CANCELLED_STATUSES)),
        func.count().filter(Reservation.status == "no_show"),
        func.count().filter(Reservation.is_walk_in.is_(True)),
        func.avg(Reservation.party_size).filter(completed),
        func.avg(
            func.extract("epoch", Reservation.completed_at - Reservation.seated_at) / 60.0
        ).filter(completed, Reservation.seated_at.isnot(None)),
        func.count().filter(Reservation.status.in_(_CONVERSION_DENOMINATOR_STATUSES)),
    ).where(for_date)
    row = (await session.execute(counts_stmt)).one()
    (
        total_count,
        upcoming_count,
        completed_count,
        cancelled_count,
        no_show_count,
        walk_in_count,
        average_party_size,
        average_dining_duration_minutes,
        conversion_denominator,
    ) = row

    conversion_rate = completed_count / conversion_denominator if conversion_denominator else None

    hourly_stmt = (
        select(func.extract("hour", Reservation.start_time), func.count())
        .where(for_date)
        .group_by(func.extract("hour", Reservation.start_time))
    )
    hourly_reservation_counts = {
        int(hour): count for hour, count in (await session.execute(hourly_stmt)).all()
    }

    area_stmt = (
        select(Reservation.dining_area_id, func.count())
        .where(for_date, Reservation.dining_area_id.isnot(None))
        .group_by(Reservation.dining_area_id)
    )
    dining_area_utilization = {
        str(area_id): count for area_id, count in (await session.execute(area_stmt)).all()
    }

    table_stmt = (
        select(ReservationTableAssignment.restaurant_table_id, func.count())
        .join(Reservation, Reservation.id == ReservationTableAssignment.reservation_id)
        .where(for_date)
        .group_by(ReservationTableAssignment.restaurant_table_id)
    )
    table_utilization = {
        str(table_id): count for table_id, count in (await session.execute(table_stmt)).all()
    }

    return ReservationDashboardStatsOut(
        target_date=target_date,
        total_count=total_count,
        upcoming_count=upcoming_count,
        completed_count=completed_count,
        cancelled_count=cancelled_count,
        no_show_count=no_show_count,
        walk_in_count=walk_in_count,
        average_party_size=float(average_party_size) if average_party_size is not None else None,
        average_dining_duration_minutes=(
            float(average_dining_duration_minutes)
            if average_dining_duration_minutes is not None
            else None
        ),
        conversion_rate=conversion_rate,
        hourly_reservation_counts=hourly_reservation_counts,
        dining_area_utilization=dining_area_utilization,
        table_utilization=table_utilization,
    )
