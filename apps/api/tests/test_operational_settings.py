"""Tests for `app.operational_settings` — the singleton settings row,
using the same "read/update never get-or-create" convention as
`app.reservations`'s `ReservationSettings`. Every test explicitly clears
existing rows first (inside the SAVEPOINT this fixture always rolls back,
so nothing real is lost) rather than assuming the table starts empty —
in a seeded dev database the singleton row already exists for real."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from app.db.models import OperationalSettings, StaffUser
from app.operational_settings.errors import OperationalSettingsNotSeededError
from app.operational_settings.service import get_operational_settings, update_operational_settings
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def test_get_operational_settings_raises_when_not_seeded(db_session: AsyncSession) -> None:
    await db_session.execute(delete(OperationalSettings))
    with pytest.raises(OperationalSettingsNotSeededError):
        await get_operational_settings(db_session)


async def test_update_operational_settings_only_touches_provided_fields(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    await db_session.execute(delete(OperationalSettings))
    settings = OperationalSettings(created_by=actor.id, updated_by=actor.id)
    db_session.add(settings)
    await db_session.flush()

    original_worker_max_jobs = settings.worker_max_jobs
    original_version = settings.version

    updated = await update_operational_settings(
        db_session, settings=settings, actor=actor, maintenance_mode_enabled=True
    )
    assert updated.maintenance_mode_enabled is True
    assert updated.worker_max_jobs == original_worker_max_jobs  # untouched
    assert updated.version == original_version + 1
    assert updated.updated_by == actor.id
