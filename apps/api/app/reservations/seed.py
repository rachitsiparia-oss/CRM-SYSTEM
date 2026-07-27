"""Idempotent development seed data for reservations, floor management, and
business configuration — PROJECT_PLAN.md section 3.3 (operating hours) and
section 3.4 (restaurant layout and capacity) are the canonical fixtures.

Follows app.orders.seed's precedent: reuse app.reservations.service (and
sibling modules) directly rather than constructing rows by hand, so seed
data exercises the exact same validation, state-machine, and audit logic
real API calls do. Dining areas, tables, business hours, and the policy/
settings singletons are plain "get or create" idempotent inserts (the same
shape app.menu.seed._get_or_create_category uses) since those are reference
data, not exercises of the reservation lifecycle itself.

PROJECT_PLAN.md section 3.4's table counts do not sum to its own stated
indoor/outdoor guest totals (72/20) — the same documented, deliberately
unforced arithmetic gap noted in DATABASE_AND_API.md's Phase 9 deviations
section; this seed reproduces the counts exactly as listed rather than
adjusting them to reconcile.
"""

import uuid
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BusinessHours,
    Customer,
    DiningArea,
    HolidayCalendar,
    Reservation,
    ReservationPolicies,
    ReservationSettings,
    ReservationWaitlist,
    RestaurantTable,
    StaffUser,
)
from app.reservations import assignment, service, tables, walkin
from app.reservations import waitlist as waitlist_service
from app.reservations.schemas import (
    ReservationCreateIn,
    WaitlistCreateIn,
    WalkInCreateIn,
)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def _customer_id(session: AsyncSession, email: str) -> uuid.UUID | None:
    result = await session.scalar(select(Customer.id).where(Customer.primary_email == email))
    return result


async def _get_or_create_dining_area(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    description: str,
    sort_order: int,
    actor: StaffUser,
) -> DiningArea:
    existing = await session.scalar(select(DiningArea).where(DiningArea.code == code))
    if existing is not None:
        return existing
    dining_area = DiningArea(
        id=uuid.uuid4(),
        code=code,
        name=name,
        description=description,
        sort_order=sort_order,
        created_by=actor.id,
    )
    session.add(dining_area)
    await session.flush()
    return dining_area


async def _get_or_create_table(
    session: AsyncSession,
    *,
    dining_area_id: uuid.UUID,
    table_number: str,
    capacity: int,
    minimum_capacity: int,
    maximum_capacity: int,
    shape: str,
    is_wheelchair_accessible: bool,
    sort_order: int,
    actor: StaffUser,
) -> RestaurantTable:
    existing = await session.scalar(
        select(RestaurantTable).where(RestaurantTable.table_number == table_number)
    )
    if existing is not None:
        return existing
    table = RestaurantTable(
        id=uuid.uuid4(),
        dining_area_id=dining_area_id,
        table_number=table_number,
        capacity=capacity,
        minimum_capacity=minimum_capacity,
        maximum_capacity=maximum_capacity,
        shape=shape,
        status="available",
        is_wheelchair_accessible=is_wheelchair_accessible,
        sort_order=sort_order,
        created_by=actor.id,
    )
    session.add(table)
    await session.flush()
    return table


# PROJECT_PLAN.md section 3.3, verbatim.
_BUSINESS_HOURS: tuple[tuple[int, time, time, bool], ...] = (
    (0, time(11, 0), time(23, 0), False),  # Monday
    (1, time(11, 0), time(23, 0), False),  # Tuesday
    (2, time(11, 0), time(23, 0), False),  # Wednesday
    (3, time(11, 0), time(23, 0), False),  # Thursday
    (4, time(11, 0), time(0, 0), True),  # Friday, closes midnight
    (5, time(10, 30), time(0, 0), True),  # Saturday, closes midnight
    (6, time(10, 30), time(23, 30), False),  # Sunday
)


async def _seed_business_hours(session: AsyncSession, actor: StaffUser) -> None:
    for day_of_week, opens_at, closes_at, closes_next_day in _BUSINESS_HOURS:
        existing = await session.scalar(
            select(BusinessHours).where(BusinessHours.day_of_week == day_of_week)
        )
        if existing is not None:
            continue
        session.add(
            BusinessHours(
                id=uuid.uuid4(),
                day_of_week=day_of_week,
                is_closed=False,
                opens_at=opens_at,
                closes_at=closes_at,
                closes_next_day=closes_next_day,
                created_by=actor.id,
            )
        )
    await session.flush()


async def _seed_holidays(session: AsyncSession, actor: StaffUser) -> None:
    holidays: tuple[tuple[date, str, bool, time | None, time | None], ...] = (
        (date(2026, 8, 15), "Independence Day", False, time(12, 0), time(22, 0)),
        (date(2026, 11, 8), "Diwali", True, None, None),
        (date(2026, 12, 25), "Christmas Day", True, None, None),
    )
    for holiday_date, name, is_closed, opens_at, closes_at in holidays:
        existing = await session.scalar(
            select(HolidayCalendar).where(
                HolidayCalendar.holiday_date == holiday_date, HolidayCalendar.deleted_at.is_(None)
            )
        )
        if existing is not None:
            continue
        session.add(
            HolidayCalendar(
                id=uuid.uuid4(),
                holiday_date=holiday_date,
                name=name,
                is_closed=is_closed,
                opens_at=opens_at,
                closes_at=closes_at,
                created_by=actor.id,
            )
        )
    await session.flush()


async def _seed_policies_and_settings(session: AsyncSession, actor: StaffUser) -> None:
    if await session.scalar(select(ReservationPolicies).limit(1)) is None:
        session.add(ReservationPolicies(id=uuid.uuid4(), created_by=actor.id))
    if await session.scalar(select(ReservationSettings).limit(1)) is None:
        session.add(
            ReservationSettings(
                id=uuid.uuid4(),
                pending_request_expiry_minutes=120,
                reminder_lead_time_minutes=120,
                created_by=actor.id,
            )
        )
    await session.flush()


async def _seed_floor(session: AsyncSession, actor: StaffUser) -> dict[str, DiningArea]:
    indoor = await _get_or_create_dining_area(
        session,
        code="indoor",
        name="Indoor Dining",
        description="Main indoor dining room.",
        sort_order=0,
        actor=actor,
    )
    outdoor = await _get_or_create_dining_area(
        session,
        code="outdoor",
        name="Outdoor Patio",
        description="Covered outdoor seating.",
        sort_order=1,
        actor=actor,
    )
    private_dining = await _get_or_create_dining_area(
        session,
        code="private_dining",
        name="Private Dining Room",
        description="PROJECT_PLAN.md section 3.4's 18-guest private group zone.",
        sort_order=2,
        actor=actor,
    )

    # 10 two-person tables.
    for i in range(1, 11):
        await _get_or_create_table(
            session,
            dining_area_id=indoor.id,
            table_number=f"IND-{i:02d}",
            capacity=2,
            minimum_capacity=1,
            maximum_capacity=2,
            shape="square",
            is_wheelchair_accessible=False,
            sort_order=i,
            actor=actor,
        )
    # 12 four-person tables — the first 4 are the documented "four
    # accessible tables" (section 3.4's Accessibility line).
    for i in range(11, 23):
        await _get_or_create_table(
            session,
            dining_area_id=indoor.id,
            table_number=f"IND-{i:02d}",
            capacity=4,
            minimum_capacity=2,
            maximum_capacity=4,
            shape="square",
            is_wheelchair_accessible=i < 15,
            sort_order=i,
            actor=actor,
        )
    # 4 six-person tables.
    for i in range(23, 27):
        await _get_or_create_table(
            session,
            dining_area_id=indoor.id,
            table_number=f"IND-{i:02d}",
            capacity=6,
            minimum_capacity=4,
            maximum_capacity=6,
            shape="rectangle",
            is_wheelchair_accessible=False,
            sort_order=i,
            actor=actor,
        )
    # 1 eight-person community table.
    await _get_or_create_table(
        session,
        dining_area_id=indoor.id,
        table_number="IND-27",
        capacity=8,
        minimum_capacity=6,
        maximum_capacity=8,
        shape="rectangle",
        is_wheelchair_accessible=False,
        sort_order=27,
        actor=actor,
    )
    # 5 outdoor four-person tables.
    for i in range(1, 6):
        await _get_or_create_table(
            session,
            dining_area_id=outdoor.id,
            table_number=f"OUT-{i:02d}",
            capacity=4,
            minimum_capacity=2,
            maximum_capacity=4,
            shape="round",
            is_wheelchair_accessible=False,
            sort_order=i,
            actor=actor,
        )
    # Private group zone — one 18-guest room.
    await _get_or_create_table(
        session,
        dining_area_id=private_dining.id,
        table_number="PVT-01",
        capacity=18,
        minimum_capacity=10,
        maximum_capacity=18,
        shape="custom",
        is_wheelchair_accessible=True,
        sort_order=1,
        actor=actor,
    )

    return {"indoor": indoor, "outdoor": outdoor, "private_dining": private_dining}


async def _advance_and_approve(
    session: AsyncSession, actor: StaffUser, reservation: Reservation
) -> None:
    """Requested -> pending_review -> approved -> confirmation_sending ->
    confirmed, then auto-assigns the best available table — the shared
    happy-path prefix every non-terminal-example reservation below runs
    through once, gated by `status == "requested"` so a rerun never
    re-executes it (mirrors app.orders.seed's `status == "draft"` gate)."""
    await service.transition_reservation(
        session,
        actor=actor,
        reservation=reservation,
        new_status="pending_review",
        reason=None,
        request=None,
    )
    await service.approve_reservation(session, actor=actor, reservation=reservation, request=None)
    await service.transition_reservation(
        session,
        actor=actor,
        reservation=reservation,
        new_status="confirmation_sending",
        reason=None,
        request=None,
    )
    await service.transition_reservation(
        session,
        actor=actor,
        reservation=reservation,
        new_status="confirmed",
        reason=None,
        request=None,
    )
    table_id = await assignment.suggest_table(session, reservation=reservation)
    if table_id is not None:
        await assignment.assign_tables(
            session, actor=actor, reservation=reservation, table_ids=[table_id], request=None
        )


async def _create_seed_reservation(
    session: AsyncSession, actor: StaffUser, *, idempotency_key: str, **kwargs: Any
) -> tuple[Reservation, bool]:
    """Returns (reservation, created_now) — `created_now` gates every
    subsequent status-progression step so reruns are no-ops."""
    existing = await session.scalar(
        select(Reservation).where(Reservation.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing, False
    payload = ReservationCreateIn(idempotency_key=idempotency_key, **kwargs)
    reservation = await service.create_reservation(
        session, actor=actor, payload=payload, request=None
    )
    return reservation, True


async def _seed_sample_reservations(
    session: AsyncSession, actor: StaffUser, dining_areas: dict[str, DiningArea]
) -> None:
    indoor_id = dining_areas["indoor"].id
    outdoor_id = dining_areas["outdoor"].id

    ananya_id = await _customer_id(session, "ananya.rao@example.test")
    rahul_id = await _customer_id(session, "rahul.mehta@example.test")
    shreya_id = await _customer_id(session, "shreya.kulkarni@example.test")
    priya_id = await _customer_id(session, "priya.sharma@example.test")
    karthik_id = await _customer_id(session, "karthik.iyer@example.test")
    brightwave_id = await _customer_id(session, "accounts@brightwave.example.test")

    today = datetime.now().date()

    # 1. requested — a fresh, not-yet-reviewed request.
    await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-requested",
        customer_id=ananya_id,
        guest_name="Ananya Rao",
        party_size=4,
        reservation_date=date(2026, 8, 1),
        start_time=time(19, 0),
        dining_area_id=indoor_id,
        source="online",
    )

    # 2. pending_review.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-pending-review",
        customer_id=rahul_id,
        guest_name="Rahul Mehta",
        party_size=2,
        reservation_date=date(2026, 8, 2),
        start_time=time(18, 30),
        dining_area_id=indoor_id,
        source="phone",
    )
    if created:
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="pending_review",
            reason=None,
            request=None,
        )

    # 3. needs_clarification.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-needs-clarification",
        customer_id=shreya_id,
        guest_name="Shreya Kulkarni",
        party_size=6,
        reservation_date=date(2026, 8, 3),
        start_time=time(19, 30),
        dining_area_id=indoor_id,
        source="whatsapp",
        special_requests="Celebrating a birthday — need to confirm cake arrangement first.",
    )
    if created:
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="pending_review",
            reason=None,
            request=None,
        )
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="needs_clarification",
            reason="Waiting on guest to confirm cake arrangement.",
            request=None,
        )

    # 4. confirmed.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-confirmed",
        customer_id=priya_id,
        guest_name="Priya Sharma",
        party_size=2,
        reservation_date=date(2026, 8, 5),
        start_time=time(20, 0),
        dining_area_id=indoor_id,
        source="online",
    )
    if created:
        await _advance_and_approve(session, actor, reservation)

    # 5. arrived — today, already confirmed and checked in.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-arrived",
        customer_id=karthik_id,
        guest_name="Karthik Iyer",
        party_size=4,
        reservation_date=today,
        start_time=time(12, 0),
        dining_area_id=indoor_id,
        source="phone",
    )
    if created:
        await _advance_and_approve(session, actor, reservation)
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="arrived",
            reason=None,
            request=None,
        )

    # 6. seated.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-seated",
        customer_id=brightwave_id,
        guest_name="Brightwave Solutions",
        party_size=2,
        reservation_date=today,
        start_time=time(12, 30),
        dining_area_id=indoor_id,
        source="staff",
    )
    if created:
        await _advance_and_approve(session, actor, reservation)
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="arrived",
            reason=None,
            request=None,
        )
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="seated",
            reason=None,
            request=None,
        )

    # 7. completed.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-completed",
        customer_id=ananya_id,
        guest_name="Ananya Rao",
        party_size=4,
        reservation_date=today,
        start_time=time(11, 15),
        dining_area_id=indoor_id,
        source="online",
    )
    if created:
        await _advance_and_approve(session, actor, reservation)
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="arrived",
            reason=None,
            request=None,
        )
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="seated",
            reason=None,
            request=None,
        )
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="completed",
            reason=None,
            request=None,
        )

    # 8. no_show.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-no-show",
        customer_id=rahul_id,
        guest_name="Rahul Mehta",
        party_size=2,
        reservation_date=today,
        start_time=time(11, 30),
        dining_area_id=outdoor_id,
        source="phone",
    )
    if created:
        await _advance_and_approve(session, actor, reservation)
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="no_show",
            reason=None,
            request=None,
        )

    # 9. cancelled_by_customer.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-cancelled-by-customer",
        customer_id=shreya_id,
        guest_name="Shreya Kulkarni",
        party_size=3,
        reservation_date=date(2026, 8, 4),
        start_time=time(19, 0),
        dining_area_id=outdoor_id,
        source="online",
    )
    if created:
        await _advance_and_approve(session, actor, reservation)
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="cancelled_by_customer",
            reason="Guest rescheduled to a later date.",
            request=None,
        )

    # 10. cancelled_by_restaurant.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-cancelled-by-restaurant",
        customer_id=priya_id,
        guest_name="Priya Sharma",
        party_size=5,
        reservation_date=date(2026, 8, 6),
        start_time=time(20, 30),
        dining_area_id=indoor_id,
        source="phone",
    )
    if created:
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="pending_review",
            reason=None,
            request=None,
        )
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="cancelled_by_restaurant",
            reason="Private event booked the indoor dining room that evening.",
            request=None,
        )

    # 11. rejected.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-rejected",
        customer_id=karthik_id,
        guest_name="Karthik Iyer",
        party_size=2,
        reservation_date=date(2026, 8, 7),
        start_time=time(21, 0),
        dining_area_id=indoor_id,
        source="whatsapp",
    )
    if created:
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="pending_review",
            reason=None,
            request=None,
        )
        await service.reject_reservation(
            session,
            actor=actor,
            reservation=reservation,
            reason="Fully booked for a private event that evening.",
            request=None,
        )

    # 12. expired — a request nobody reviewed in time.
    reservation, created = await _create_seed_reservation(
        session,
        actor,
        idempotency_key="seed-reservation-expired",
        customer_id=None,
        guest_name="Deepak Verma",
        phone_e164="9845012345",
        party_size=2,
        reservation_date=date(2026, 8, 8),
        start_time=time(18, 0),
        dining_area_id=indoor_id,
        source="online",
    )
    if created:
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="pending_review",
            reason=None,
            request=None,
        )
        await service.transition_reservation(
            session,
            actor=actor,
            reservation=reservation,
            new_status="expired",
            reason="No review completed within the configured request window.",
            request=None,
        )


async def _seed_walk_in(
    session: AsyncSession, actor: StaffUser, dining_areas: dict[str, DiningArea]
) -> None:
    today = datetime.now().date()
    existing = await session.scalar(
        select(Reservation).where(
            Reservation.is_walk_in.is_(True),
            Reservation.guest_name == "Rohit Bhandari",
            Reservation.reservation_date == today,
        )
    )
    if existing is not None:
        return
    await walkin.create_walk_in(
        session,
        actor=actor,
        payload=WalkInCreateIn(
            guest_name="Rohit Bhandari",
            phone_e164="9900112233",
            party_size=2,
            dining_area_id=dining_areas["indoor"].id,
        ),
        request=None,
    )


async def _seed_merged_tables(session: AsyncSession, actor: StaffUser) -> None:
    primary = await session.scalar(
        select(RestaurantTable).where(RestaurantTable.table_number == "IND-23")
    )
    secondary = await session.scalar(
        select(RestaurantTable).where(RestaurantTable.table_number == "IND-24")
    )
    if primary is None or secondary is None or secondary.merged_with_table_id is not None:
        return
    await tables.merge_tables(
        session,
        actor=actor,
        primary_table=primary,
        secondary_table_ids=[secondary.id],
        reason="Combined for a 10-guest anniversary party.",
        request=None,
    )


async def _seed_waitlist(
    session: AsyncSession, actor: StaffUser, dining_areas: dict[str, DiningArea]
) -> None:
    existing = await session.scalar(
        select(ReservationWaitlist).where(ReservationWaitlist.guest_name == "Neha Kapoor")
    )
    if existing is not None:
        return
    await waitlist_service.add_to_waitlist(
        session,
        actor=actor,
        payload=WaitlistCreateIn(
            guest_name="Neha Kapoor",
            phone_e164="9871234560",
            party_size=4,
            dining_area_id=dining_areas["indoor"].id,
            priority=0,
            estimated_wait_minutes=20,
            notes="Waiting for a window table.",
        ),
        request=None,
    )


async def seed_reservations(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    await _seed_business_hours(session, actor)
    await _seed_holidays(session, actor)
    await _seed_policies_and_settings(session, actor)
    dining_areas = await _seed_floor(session, actor)
    await _seed_sample_reservations(session, actor, dining_areas)
    await _seed_walk_in(session, actor, dining_areas)
    await _seed_merged_tables(session, actor)
    await _seed_waitlist(session, actor, dining_areas)
