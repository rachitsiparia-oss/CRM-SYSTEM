import uuid
from datetime import date, time

import pytest
from app.db.models import DiningArea, Reservation, ReservationTableAssignment, RestaurantTable
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _dining_area_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {"id": uuid.uuid4(), "code": f"area-{suffix}", "name": "Test Area"}
    base.update(overrides)
    return base


async def _make_dining_area(session: AsyncSession, **overrides: object) -> DiningArea:
    dining_area = DiningArea(**_dining_area_kwargs(**overrides))
    session.add(dining_area)
    await session.flush()
    return dining_area


def _table_kwargs(dining_area_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "dining_area_id": dining_area_id,
        "table_number": f"T-{suffix}",
        "capacity": 4,
        "status": "available",
    }
    base.update(overrides)
    return base


async def _make_table(
    session: AsyncSession, dining_area_id: uuid.UUID, **overrides: object
) -> RestaurantTable:
    table = RestaurantTable(**_table_kwargs(dining_area_id, **overrides))
    session.add(table)
    await session.flush()
    return table


def _reservation_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "reservation_number": f"RES-{suffix}",
        "guest_name": "Test Guest",
        "party_size": 2,
        "reservation_date": date(2026, 8, 1),
        "start_time": time(19, 0),
        "status": "requested",
        "source": "phone",
    }
    base.update(overrides)
    return base


async def _make_reservation(session: AsyncSession, **overrides: object) -> Reservation:
    reservation = Reservation(**_reservation_kwargs(**overrides))
    session.add(reservation)
    await session.flush()
    return reservation


# --- RestaurantTable ----------------------------------------------------


async def test_table_rejects_invalid_status(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    db_session.add(RestaurantTable(**_table_kwargs(dining_area.id, status="on_fire")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_table_rejects_invalid_shape(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    db_session.add(RestaurantTable(**_table_kwargs(dining_area.id, shape="triangle")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_table_rejects_non_positive_capacity(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    db_session.add(RestaurantTable(**_table_kwargs(dining_area.id, capacity=0)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_table_rejects_maximum_capacity_below_capacity(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    db_session.add(RestaurantTable(**_table_kwargs(dining_area.id, capacity=6, maximum_capacity=4)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_table_rejects_minimum_capacity_above_capacity(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    db_session.add(RestaurantTable(**_table_kwargs(dining_area.id, capacity=2, minimum_capacity=4)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_table_number_unique_among_active_tables(db_session: AsyncSession) -> None:
    dining_area = await _make_dining_area(db_session)
    await _make_table(db_session, dining_area.id, table_number="DUP-1")
    db_session.add(RestaurantTable(**_table_kwargs(dining_area.id, table_number="DUP-1")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- Reservation --------------------------------------------------------


async def test_reservation_rejects_invalid_status(db_session: AsyncSession) -> None:
    db_session.add(Reservation(**_reservation_kwargs(status="floating_around")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_reservation_rejects_invalid_source(db_session: AsyncSession) -> None:
    db_session.add(Reservation(**_reservation_kwargs(source="carrier_pigeon")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_reservation_rejects_non_positive_party_size(db_session: AsyncSession) -> None:
    db_session.add(Reservation(**_reservation_kwargs(party_size=0)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_reservation_rejects_end_time_before_start_time(db_session: AsyncSession) -> None:
    db_session.add(Reservation(**_reservation_kwargs(start_time=time(20, 0), end_time=time(19, 0))))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_reservation_rejects_negative_deposit(db_session: AsyncSession) -> None:
    db_session.add(Reservation(**_reservation_kwargs(deposit_amount_minor=-100)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_reservation_number_is_unique(db_session: AsyncSession) -> None:
    reservation = await _make_reservation(db_session)
    db_session.add(
        Reservation(**_reservation_kwargs(reservation_number=reservation.reservation_number))
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_reservation_idempotency_key_unique_when_set(db_session: AsyncSession) -> None:
    await _make_reservation(db_session, idempotency_key="dup-key")
    db_session.add(Reservation(**_reservation_kwargs(idempotency_key="dup-key")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_reservation_idempotency_key_null_does_not_collide(db_session: AsyncSession) -> None:
    await _make_reservation(db_session, idempotency_key=None)
    # Should not raise — multiple NULLs are allowed under the partial unique index.
    await _make_reservation(db_session, idempotency_key=None)


# --- ReservationTableAssignment ------------------------------------------


async def test_only_one_active_assignment_per_reservation_table_pair(
    db_session: AsyncSession,
) -> None:
    dining_area = await _make_dining_area(db_session)
    table = await _make_table(db_session, dining_area.id)
    reservation = await _make_reservation(db_session)
    db_session.add(
        ReservationTableAssignment(
            id=uuid.uuid4(), reservation_id=reservation.id, restaurant_table_id=table.id
        )
    )
    await db_session.flush()
    db_session.add(
        ReservationTableAssignment(
            id=uuid.uuid4(), reservation_id=reservation.id, restaurant_table_id=table.id
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
