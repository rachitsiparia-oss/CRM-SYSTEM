from typing import Any

from app.reservations.reminders import dispatch_reservation_reminders
from app.reservations.waitlist import expire_stale_waitlist_entries
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def send_reservation_reminders(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await dispatch_reservation_reminders(session)
        return {"reminders_sent": count}

    return await run_scheduled_job(
        job_type="reservations.dispatch_reminders",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )


async def expire_waitlist(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await expire_stale_waitlist_entries(session)
        return {"entries_expired": count}

    return await run_scheduled_job(
        job_type="reservations.expire_waitlist",
        queue_name="critical-domain",
        func=_run,
        max_attempts=3,
        timeout_seconds=120,
    )
