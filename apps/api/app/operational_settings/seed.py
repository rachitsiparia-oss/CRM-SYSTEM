"""Idempotent development seed data — creates the single
`OperationalSettings` row if it does not already exist, matching the same
singleton-guard seed convention `app.reservations.seed`'s
`_seed_policies_and_settings` established for `ReservationSettings`. Every
field is left at its model default; this seed's only job is to make sure
the row exists at all, since `app.operational_settings.service` never
get-or-creates."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OperationalSettings, StaffUser


async def seed_operational_settings(session: AsyncSession) -> None:
    if await session.scalar(select(OperationalSettings).limit(1)) is not None:
        return

    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    if actor is None:
        return

    session.add(OperationalSettings(created_by=actor.id, updated_by=actor.id))
    await session.flush()
