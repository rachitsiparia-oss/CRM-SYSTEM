import uuid
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from app.db.models import (
    BusinessHours,
    DiningArea,
    Reservation,
    ReservationTableAssignment,
    RestaurantTable,
    TableBlock,
)
from app.reservations.availability import (
    find_available_tables,
    is_table_available,
    is_within_operating_hours,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

_MONDAY = date(2026, 8, 3)  # A known Monday, independent of "today".


async def _make_dining_area(session: AsyncSession) -> DiningArea:
    suffix = uuid.uuid4().hex[:10]
    dining_area = DiningArea(id=uuid.uuid4(), code=f"area-{suffix}", name="Test Area")
    session.add(dining_area)
    await session.flush()
    return dining_area


async def _make_table(
    session: AsyncSession, dining_area_id: uuid.UUID, **overrides: object
) -> RestaurantTable:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "dining_area_id": dining_area_id,
        "table_number": f"T-{suffix}",
        "capacity": 4,
        "minimum_capacity": 1,
        "status": "available",
    }
    base.update(overrides)
    table = RestaurantTable(**base)
    session.add(table)
    await session.flush()
    return table


async def _make_reservation(session: AsyncSession, **overrides: object) -> Reservation:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "reservation_number": f"RES-{suffix}",
        "guest_name": "Test Guest",
        "party_size": 2,
        "reservation_date": _MONDAY,
        "start_time": time(19, 0),
        "status": "confirmed",
        "source": "phone",
    }
    base.update(overrides)
    reservation = Reservation(**base)
    session.add(reservation)
    await session.flush()
    return reservation


async def _assign(session: AsyncSession, reservation_id: uuid.UUID, table_id: uuid.UUID) -> None:
    session.add(
        ReservationTableAssignment(
            id=uuid.uuid4(), reservation_id=reservation_id, restaurant_table_id=table_id
        )
    )
    await session.flush()


async def _set_monday_hours(session: AsyncSession, *, is_closed: bool = False) -> None:
    # The live/seeded database already has a business_hours row for every
    # day of week (a hard uniqueness constraint on day_of_week) — update
    # the existing row in place rather than inserting a second one.
    existing = await session.scalar(
        select(BusinessHours).where(BusinessHours.day_of_week == _MONDAY.weekday())
    )
    if existing is None:
        session.add(
            BusinessHours(
                id=uuid.uuid4(),
                day_of_week=_MONDAY.weekday(),
                is_closed=is_closed,
                opens_at=None if is_closed else time(11, 0),
                closes_at=None if is_closed else time(23, 0),
            )
        )
    else:
        existing.is_closed = is_closed
        existing.opens_at = None if is_closed else time(11, 0)
        existing.closes_at = None if is_closed else time(23, 0)
        existing.closes_next_day = False
    await session.flush()


async def _clear_monday_hours(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(BusinessHours).where(BusinessHours.day_of_week == _MONDAY.weekday())
    )
    if existing is not None:
        await session.delete(existing)
        await session.flush()


# --- is_within_operating_hours -------------------------------------------


async def test_no_business_hours_row_fails_closed(db_session: AsyncSession) -> None:
    await _clear_monday_hours(db_session)
    assert not await is_within_operating_hours(
        db_session, target_date=_MONDAY, start_time=time(19, 0), end_time=time(20, 0)
    )


async def test_within_configured_hours(db_session: AsyncSession) -> None:
    await _set_monday_hours(db_session)
    assert await is_within_operating_hours(
        db_session, target_date=_MONDAY, start_time=time(19, 0), end_time=time(20, 0)
    )


async def test_before_opening_is_rejected(db_session: AsyncSession) -> None:
    await _set_monday_hours(db_session)
    assert not await is_within_operating_hours(
        db_session, target_date=_MONDAY, start_time=time(9, 0), end_time=time(10, 0)
    )


async def test_after_closing_is_rejected(db_session: AsyncSession) -> None:
    await _set_monday_hours(db_session)
    assert not await is_within_operating_hours(
        db_session, target_date=_MONDAY, start_time=time(22, 30), end_time=time(23, 30)
    )


async def test_closed_day_rejects_everything(db_session: AsyncSession) -> None:
    await _set_monday_hours(db_session, is_closed=True)
    assert not await is_within_operating_hours(
        db_session, target_date=_MONDAY, start_time=time(12, 0), end_time=time(13, 0)
    )


# --- is_table_available / find_available_tables ---------------------------


async def test_table_available_with_no_conflicts(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    table = await _make_table(db_session, dining_area.id, capacity=4)
    assert await is_table_available(
        db_session,
        table=table,
        target_date=_MONDAY,
        start_time=time(19, 0),
        end_time=time(20, 0),
        party_size=2,
    )


async def test_table_rejected_when_party_exceeds_capacity(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    table = await _make_table(db_session, dining_area.id, capacity=2, maximum_capacity=2)
    assert not await is_table_available(
        db_session,
        table=table,
        target_date=_MONDAY,
        start_time=time(19, 0),
        end_time=time(20, 0),
        party_size=6,
    )


async def test_table_rejected_when_status_unavailable(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    table = await _make_table(db_session, dining_area.id, status="maintenance")
    assert not await is_table_available(
        db_session,
        table=table,
        target_date=_MONDAY,
        start_time=time(19, 0),
        end_time=time(20, 0),
        party_size=2,
    )


async def test_table_rejected_for_overlapping_reservation(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    table = await _make_table(db_session, dining_area.id)
    existing = await _make_reservation(
        db_session, reservation_date=_MONDAY, start_time=time(19, 0), end_time=time(20, 30)
    )
    await _assign(db_session, existing.id, table.id)

    assert not await is_table_available(
        db_session,
        table=table,
        target_date=_MONDAY,
        start_time=time(19, 30),
        end_time=time(21, 0),
        party_size=2,
    )


async def test_table_available_outside_buffered_window(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    table = await _make_table(db_session, dining_area.id)
    existing = await _make_reservation(
        db_session, reservation_date=_MONDAY, start_time=time(19, 0), end_time=time(20, 0)
    )
    await _assign(db_session, existing.id, table.id)

    # The seeded/default buffer is 15 minutes either side — a slot starting
    # well after the buffered window clears should be free.
    assert await is_table_available(
        db_session,
        table=table,
        target_date=_MONDAY,
        start_time=time(20, 30),
        end_time=time(21, 30),
        party_size=2,
    )


async def test_cancelled_reservation_does_not_block_the_table(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    table = await _make_table(db_session, dining_area.id)
    cancelled = await _make_reservation(
        db_session,
        reservation_date=_MONDAY,
        start_time=time(19, 0),
        end_time=time(20, 0),
        status="cancelled_by_customer",
    )
    await _assign(db_session, cancelled.id, table.id)

    assert await is_table_available(
        db_session,
        table=table,
        target_date=_MONDAY,
        start_time=time(19, 0),
        end_time=time(20, 0),
        party_size=2,
    )


async def test_active_table_block_excludes_the_table(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    table = await _make_table(db_session, dining_area.id)
    db_session.add(
        TableBlock(
            id=uuid.uuid4(),
            restaurant_table_id=table.id,
            block_type="private_event",
            starts_at=datetime(2026, 8, 3, 18, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
            ends_at=datetime(2026, 8, 3, 22, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
            is_active=True,
        )
    )
    await db_session.flush()

    assert not await is_table_available(
        db_session,
        table=table,
        target_date=_MONDAY,
        start_time=time(19, 0),
        end_time=time(20, 0),
        party_size=2,
    )


async def test_find_available_tables_filters_by_dining_area(db_session: AsyncSession) -> None:
    area_a = await _make_dining_area(db_session)
    area_b = await _make_dining_area(db_session)
    table_a = await _make_table(db_session, area_a.id)
    await _make_table(db_session, area_b.id)

    results = await find_available_tables(
        db_session,
        target_date=_MONDAY,
        start_time=time(19, 0),
        end_time=time(20, 0),
        party_size=2,
        dining_area_id=area_a.id,
    )
    assert [t.id for t in results] == [table_a.id]


async def test_find_available_tables_prefers_closest_capacity_fit(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    small = await _make_table(
        db_session, dining_area.id, capacity=2, maximum_capacity=2, sort_order=1
    )
    large = await _make_table(
        db_session, dining_area.id, capacity=8, maximum_capacity=8, sort_order=2
    )

    results = await find_available_tables(
        db_session,
        target_date=_MONDAY,
        start_time=time(19, 0),
        end_time=time(20, 0),
        party_size=2,
        dining_area_id=dining_area.id,
    )
    assert results[0].id == small.id
    assert results[-1].id == large.id
