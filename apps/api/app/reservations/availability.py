"""The availability and conflict-detection engine — this phase's own
"never overbook" requirement, and PROJECT_PLAN.md section 11.2's "Approval
checks capacity, time, seating zone, special requests, operating hours, and
conflicts." Pure, callable functions only (the "engine, not scheduler"
principle this phase applies elsewhere) — nothing here runs on a timer.

Conflict detection combines two independent signals per table, since each
covers a case the other misses:
  1. Other active reservations holding that table via
     `ReservationTableAssignment` for an overlapping date/time window
     (correct for any future date).
  2. `TableBlock` rows whose own `starts_at`/`ends_at` window overlaps —
     catches a block scheduled for a *different* date than "right now".
A table currently `blocked`/`maintenance`/`merged` (its live `status`
column) is excluded from every date's availability outright: an ad hoc
block created via `transition_table_status` rather than
`create_table_block` has no defined end time, so there is no way to know it
clears before some future date — excluding it everywhere is the
fail-closed choice CLAUDE.md section 24 favors over risking a double
booking.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BusinessHours,
    HolidayCalendar,
    Reservation,
    ReservationPolicies,
    ReservationSettings,
    ReservationTableAssignment,
    RestaurantTable,
    TableBlock,
)

# Statuses that still hold a real claim on a table's time — everything else
# (rejected/cancelled_by_*/no_show/expired) has released it.
_ACTIVE_RESERVATION_STATUSES = frozenset(
    {
        "requested",
        "pending_review",
        "needs_clarification",
        "approved",
        "confirmation_sending",
        "confirmed",
        "reminder_scheduled",
        "arrived",
        "seated",
    }
)

_UNAVAILABLE_TABLE_STATUSES = frozenset({"blocked", "maintenance", "merged"})

# Matches the corresponding singleton settings' own column defaults — used
# only before that row has been seeded (see app.reservations.service's
# identical fallback pattern for ReservationPolicies).
_DEFAULT_BUFFER_BEFORE_MINUTES = 15
_DEFAULT_BUFFER_AFTER_MINUTES = 15
_DEFAULT_RESERVATION_DURATION_MINUTES = 90

# CLAUDE.md section 7: timestamps are stored in UTC, but `Reservation.
# reservation_date`/`start_time`/`end_time` are the restaurant's own local
# wall-clock booking (the same convention app.orders.service and
# app.reservations.walkin already use for "today"). `TableBlock.starts_at`/
# `ends_at` are genuine tz-aware UTC instants, so every window built here is
# localized to this zone before comparison — comparing a naive local
# wall-clock window against a tz-aware UTC one raises TypeError in Python,
# and silently treating them as the same instant would be wrong whenever
# IST's +05:30 offset actually matters (any block window near local
# midnight).
_RESTAURANT_TIMEZONE = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class TimeWindow:
    starts_at: datetime
    ends_at: datetime


async def _get_buffers(session: AsyncSession) -> tuple[int, int]:
    policies = await session.scalar(select(ReservationPolicies).limit(1))
    if policies is None:
        return _DEFAULT_BUFFER_BEFORE_MINUTES, _DEFAULT_BUFFER_AFTER_MINUTES
    return policies.buffer_before_minutes, policies.buffer_after_minutes


async def _get_default_duration_minutes(session: AsyncSession) -> int:
    settings = await session.scalar(select(ReservationSettings).limit(1))
    if settings is None:
        return _DEFAULT_RESERVATION_DURATION_MINUTES
    return settings.default_reservation_duration_minutes


def _resolve_window(
    *, target_date: date, start_time: time, end_time: time | None, default_duration_minutes: int
) -> tuple[datetime, datetime]:
    starts_at = datetime.combine(target_date, start_time, tzinfo=_RESTAURANT_TIMEZONE)
    if end_time is not None:
        ends_at = datetime.combine(target_date, end_time, tzinfo=_RESTAURANT_TIMEZONE)
        if ends_at <= starts_at:
            ends_at += timedelta(days=1)
    else:
        ends_at = starts_at + timedelta(minutes=default_duration_minutes)
    return starts_at, ends_at


def _windows_overlap(a: TimeWindow, b: TimeWindow) -> bool:
    return a.starts_at < b.ends_at and b.starts_at < a.ends_at


async def get_business_hours_for_date(
    session: AsyncSession, target_date: date
) -> tuple[BusinessHours | None, HolidayCalendar | None]:
    holiday = await session.scalar(
        select(HolidayCalendar).where(
            HolidayCalendar.holiday_date == target_date, HolidayCalendar.deleted_at.is_(None)
        )
    )
    business_hours = await session.scalar(
        select(BusinessHours).where(BusinessHours.day_of_week == target_date.weekday())
    )
    return business_hours, holiday


async def is_within_operating_hours(
    session: AsyncSession, *, target_date: date, start_time: time, end_time: time | None
) -> bool:
    business_hours, holiday = await get_business_hours_for_date(session, target_date)

    if holiday is not None:
        if holiday.is_closed:
            return False
        opens_at, closes_at = holiday.opens_at, holiday.closes_at
    elif business_hours is not None:
        if business_hours.is_closed:
            return False
        opens_at, closes_at = business_hours.opens_at, business_hours.closes_at
    else:
        # No configured hours row for this day at all — fail closed rather
        # than silently accepting a booking outside unmanaged hours.
        return False

    if opens_at is None or closes_at is None:
        return False
    if start_time < opens_at:
        return False
    check_end = end_time if end_time is not None else start_time
    closes_next_day = (
        business_hours.closes_next_day if holiday is None and business_hours else False
    )
    if closes_next_day:
        return True
    return check_end <= closes_at


async def get_table_conflicts(
    session: AsyncSession,
    *,
    table_id: uuid.UUID,
    target_date: date,
    start_time: time,
    end_time: time | None,
    exclude_reservation_id: uuid.UUID | None = None,
) -> list[Reservation]:
    buffer_before, buffer_after = await _get_buffers(session)
    default_duration = await _get_default_duration_minutes(session)
    starts_at, ends_at = _resolve_window(
        target_date=target_date,
        start_time=start_time,
        end_time=end_time,
        default_duration_minutes=default_duration,
    )
    requested_window = TimeWindow(
        starts_at=starts_at - timedelta(minutes=buffer_before),
        ends_at=ends_at + timedelta(minutes=buffer_after),
    )

    stmt = (
        select(Reservation)
        .join(
            ReservationTableAssignment,
            ReservationTableAssignment.reservation_id == Reservation.id,
        )
        .where(
            ReservationTableAssignment.restaurant_table_id == table_id,
            ReservationTableAssignment.unassigned_at.is_(None),
            Reservation.reservation_date == target_date,
            Reservation.status.in_(_ACTIVE_RESERVATION_STATUSES),
        )
    )
    if exclude_reservation_id is not None:
        stmt = stmt.where(Reservation.id != exclude_reservation_id)

    candidates = (await session.scalars(stmt)).all()
    conflicts = []
    for candidate in candidates:
        candidate_starts_at, candidate_ends_at = _resolve_window(
            target_date=candidate.reservation_date,
            start_time=candidate.start_time,
            end_time=candidate.end_time,
            default_duration_minutes=default_duration,
        )
        candidate_window = TimeWindow(starts_at=candidate_starts_at, ends_at=candidate_ends_at)
        if _windows_overlap(requested_window, candidate_window):
            conflicts.append(candidate)
    return conflicts


async def get_table_block_conflicts(
    session: AsyncSession,
    *,
    table_id: uuid.UUID,
    target_date: date,
    start_time: time,
    end_time: time | None,
) -> list[TableBlock]:
    default_duration = await _get_default_duration_minutes(session)
    starts_at, ends_at = _resolve_window(
        target_date=target_date,
        start_time=start_time,
        end_time=end_time,
        default_duration_minutes=default_duration,
    )
    requested_window = TimeWindow(starts_at=starts_at, ends_at=ends_at)

    blocks = (
        await session.scalars(
            select(TableBlock).where(
                TableBlock.restaurant_table_id == table_id, TableBlock.is_active.is_(True)
            )
        )
    ).all()
    return [
        block
        for block in blocks
        if _windows_overlap(
            requested_window, TimeWindow(starts_at=block.starts_at, ends_at=block.ends_at)
        )
    ]


async def is_table_available(
    session: AsyncSession,
    *,
    table: RestaurantTable,
    target_date: date,
    start_time: time,
    end_time: time | None,
    party_size: int,
    exclude_reservation_id: uuid.UUID | None = None,
) -> bool:
    if table.deleted_at is not None or not table.is_active:
        return False
    if table.status in _UNAVAILABLE_TABLE_STATUSES:
        return False
    if party_size < table.minimum_capacity:
        return False
    if party_size > (table.maximum_capacity or table.capacity):
        return False

    reservation_conflicts = await get_table_conflicts(
        session,
        table_id=table.id,
        target_date=target_date,
        start_time=start_time,
        end_time=end_time,
        exclude_reservation_id=exclude_reservation_id,
    )
    if reservation_conflicts:
        return False

    block_conflicts = await get_table_block_conflicts(
        session,
        table_id=table.id,
        target_date=target_date,
        start_time=start_time,
        end_time=end_time,
    )
    return not block_conflicts


async def find_available_tables(
    session: AsyncSession,
    *,
    target_date: date,
    start_time: time,
    end_time: time | None,
    party_size: int,
    dining_area_id: uuid.UUID | None = None,
    exclude_reservation_id: uuid.UUID | None = None,
) -> list[RestaurantTable]:
    stmt = select(RestaurantTable).where(
        RestaurantTable.deleted_at.is_(None), RestaurantTable.is_active.is_(True)
    )
    if dining_area_id is not None:
        stmt = stmt.where(RestaurantTable.dining_area_id == dining_area_id)

    candidates = (await session.scalars(stmt)).all()
    available = []
    for table in candidates:
        if await is_table_available(
            session,
            table=table,
            target_date=target_date,
            start_time=start_time,
            end_time=end_time,
            party_size=party_size,
            exclude_reservation_id=exclude_reservation_id,
        ):
            available.append(table)
    # Best options first: closest-fitting capacity, then lowest sort_order —
    # avoids seating a party of 2 at the community table when a two-top is
    # free.
    available.sort(key=lambda t: (t.capacity, t.sort_order))
    return available
