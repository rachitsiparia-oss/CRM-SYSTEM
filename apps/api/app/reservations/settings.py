"""Business hours, holiday calendar, and reservation policy/settings
services. `BusinessHours` and the two singleton settings tables
(`ReservationPolicies`/`ReservationSettings`) are update-only here: exactly
seven `BusinessHours` rows and one row each of the singletons exist at all
times (seeded once — task #111), so there is no create/delete path, only
`update_*`. `HolidayCalendar` is a genuine managed reference list and
mirrors `app.reservations.tables.create_dining_area`'s create/update/
archive/restore shape.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    BusinessHours,
    HolidayCalendar,
    ReservationPolicies,
    ReservationSettings,
    StaffUser,
)
from app.reservations.schemas import (
    BusinessHoursUpdateIn,
    HolidayCalendarCreateIn,
    HolidayCalendarUpdateIn,
    ReservationPoliciesUpdateIn,
    ReservationSettingsUpdateIn,
)


def _apply_optimistic_update(
    entity: BusinessHours | HolidayCalendar | ReservationPolicies | ReservationSettings,
    *,
    expected_version: int | None,
    updates: dict[str, object],
    actor_id: uuid.UUID,
    entity_label: str,
) -> dict[str, object]:
    if expected_version is not None and expected_version != entity.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This {entity_label} was updated by someone else. Reload and try again.",
        )
    before = {field: getattr(entity, field) for field in updates}
    for field, value in updates.items():
        setattr(entity, field, value)
    if updates:
        entity.version += 1
        entity.updated_by = actor_id
    return before


# --- Business hours -----------------------------------------------------


async def update_business_hours(
    session: AsyncSession,
    *,
    actor: StaffUser,
    business_hours: BusinessHours,
    payload: BusinessHoursUpdateIn,
    request: Request | None,
) -> BusinessHours:
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = _apply_optimistic_update(
        business_hours,
        expected_version=payload.expected_version,
        updates=updates,
        actor_id=actor.id,
        entity_label="business hours",
    )
    if updates:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="business_hours.updated",
            target_type="business_hours",
            target_id=business_hours.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return business_hours


# --- Holiday calendar -----------------------------------------------------


async def create_holiday(
    session: AsyncSession,
    *,
    actor: StaffUser,
    payload: HolidayCalendarCreateIn,
    request: Request | None,
) -> HolidayCalendar:
    holiday = HolidayCalendar(
        id=uuid.uuid4(),
        holiday_date=payload.holiday_date,
        name=payload.name,
        is_closed=payload.is_closed,
        opens_at=payload.opens_at,
        closes_at=payload.closes_at,
        notes=payload.notes,
        created_by=actor.id,
    )
    session.add(holiday)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="holiday_calendar.created",
        target_type="holiday_calendar",
        target_id=holiday.id,
        request=request,
        safe_metadata={"holiday_date": holiday.holiday_date.isoformat()},
    )
    return holiday


async def update_holiday(
    session: AsyncSession,
    *,
    actor: StaffUser,
    holiday: HolidayCalendar,
    payload: HolidayCalendarUpdateIn,
    request: Request | None,
) -> HolidayCalendar:
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = _apply_optimistic_update(
        holiday,
        expected_version=payload.expected_version,
        updates=updates,
        actor_id=actor.id,
        entity_label="holiday",
    )
    if updates:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="holiday_calendar.updated",
            target_type="holiday_calendar",
            target_id=holiday.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return holiday


async def archive_holiday(
    session: AsyncSession,
    *,
    actor: StaffUser,
    holiday: HolidayCalendar,
    reason: str,
    request: Request | None,
) -> None:
    holiday.deleted_at = datetime.now(UTC)
    holiday.deleted_by = actor.id
    holiday.deletion_reason = reason
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="holiday_calendar.archived",
        target_type="holiday_calendar",
        target_id=holiday.id,
        request=request,
        safe_metadata={"reason": reason},
    )


async def restore_holiday(
    session: AsyncSession, *, actor: StaffUser, holiday: HolidayCalendar, request: Request | None
) -> None:
    holiday.deleted_at = None
    holiday.deleted_by = None
    holiday.deletion_reason = None
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="holiday_calendar.restored",
        target_type="holiday_calendar",
        target_id=holiday.id,
        request=request,
    )


# --- Policies and settings singletons ---------------------------------------


async def update_reservation_policies(
    session: AsyncSession,
    *,
    actor: StaffUser,
    policies: ReservationPolicies,
    payload: ReservationPoliciesUpdateIn,
    request: Request | None,
) -> ReservationPolicies:
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = _apply_optimistic_update(
        policies,
        expected_version=payload.expected_version,
        updates=updates,
        actor_id=actor.id,
        entity_label="reservation policies",
    )
    if updates:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="reservation_policies.updated",
            target_type="reservation_policies",
            target_id=policies.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return policies


async def update_reservation_settings(
    session: AsyncSession,
    *,
    actor: StaffUser,
    settings: ReservationSettings,
    payload: ReservationSettingsUpdateIn,
    request: Request | None,
) -> ReservationSettings:
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = _apply_optimistic_update(
        settings,
        expected_version=payload.expected_version,
        updates=updates,
        actor_id=actor.id,
        entity_label="reservation settings",
    )
    if updates:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="reservation_settings.updated",
            target_type="reservation_settings",
            target_id=settings.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return settings
