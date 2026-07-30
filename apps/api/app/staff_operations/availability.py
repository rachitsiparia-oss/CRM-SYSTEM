"""Staff availability windows — this phase's own instruction section 27,
lightweight roster-planning input, not automatic roster optimization."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StaffAvailabilityWindow, StaffUser
from app.staff_operations.schemas import AvailabilityWindowCreateIn


async def create_availability_window(
    session: AsyncSession,
    *,
    actor: StaffUser,
    staff_user_id: uuid.UUID,
    payload: AvailabilityWindowCreateIn,
) -> StaffAvailabilityWindow:
    window = StaffAvailabilityWindow(
        staff_user_id=staff_user_id,
        availability_type=payload.availability_type,
        day_of_week=payload.day_of_week,
        specific_date=payload.specific_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reason=payload.reason,
        effective_start_date=payload.effective_start_date,
        effective_end_date=payload.effective_end_date,
        created_by=actor.id,
    )
    session.add(window)
    await session.flush()
    return window


async def list_availability_windows(
    session: AsyncSession, staff_user_id: uuid.UUID
) -> list[StaffAvailabilityWindow]:
    result = await session.scalars(
        select(StaffAvailabilityWindow).where(
            StaffAvailabilityWindow.staff_user_id == staff_user_id
        )
    )
    return list(result.all())


async def delete_availability_window(
    session: AsyncSession, window: StaffAvailabilityWindow
) -> None:
    await session.delete(window)
    await session.flush()
