"""Operational settings singleton — worker limits, retry defaults, queue
priority weighting, notification channel permissions, maintenance mode,
and AI provider selection. Same "seed creates the one row, read/update
never get-or-create" convention `app.reservations`'s
`ReservationSettings`/`ReservationPolicies` already established.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import build_key
from app.cache.service import delete as cache_delete
from app.db.models import OperationalSettings, StaffUser
from app.operational_settings.errors import OperationalSettingsNotSeededError

_CACHE_KEY = build_key("settings", "operational")


async def get_operational_settings(session: AsyncSession) -> OperationalSettings:
    settings = await session.scalar(select(OperationalSettings).limit(1))
    if settings is None:
        raise OperationalSettingsNotSeededError("Operational settings have not been seeded.")
    return settings


async def update_operational_settings(
    session: AsyncSession,
    *,
    settings: OperationalSettings,
    actor: StaffUser,
    maintenance_mode_enabled: bool | None = None,
    maintenance_message: str | None = None,
    scheduler_enabled: bool | None = None,
    default_max_attempts: int | None = None,
    default_retry_backoff_seconds: int | None = None,
    default_retry_backoff_cap_seconds: int | None = None,
    worker_max_jobs: int | None = None,
    worker_job_timeout_seconds: int | None = None,
    queue_priority_config: dict[str, Any] | None = None,
    notification_channel_config: dict[str, Any] | None = None,
    active_ai_provider_code: str | None = None,
) -> OperationalSettings:
    updates = {
        "maintenance_mode_enabled": maintenance_mode_enabled,
        "maintenance_message": maintenance_message,
        "scheduler_enabled": scheduler_enabled,
        "default_max_attempts": default_max_attempts,
        "default_retry_backoff_seconds": default_retry_backoff_seconds,
        "default_retry_backoff_cap_seconds": default_retry_backoff_cap_seconds,
        "worker_max_jobs": worker_max_jobs,
        "worker_job_timeout_seconds": worker_job_timeout_seconds,
        "queue_priority_config": queue_priority_config,
        "notification_channel_config": notification_channel_config,
        "active_ai_provider_code": active_ai_provider_code,
    }
    for field, value in updates.items():
        if value is not None:
            setattr(settings, field, value)
    settings.updated_by = actor.id
    settings.version += 1
    await session.flush()
    await cache_delete(_CACHE_KEY)
    return settings
