from typing import Any

from app.notifications.dispatch import dispatch_pending_notification_deliveries
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def dispatch_notification_deliveries(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        return dict(await dispatch_pending_notification_deliveries(session))

    return await run_scheduled_job(
        job_type="notifications.dispatch_pending_deliveries",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )
