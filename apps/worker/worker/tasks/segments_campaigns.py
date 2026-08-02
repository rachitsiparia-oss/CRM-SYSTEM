from typing import Any

from app.campaigns.execution import sync_all_running_campaigns
from app.segments.membership import refresh_all_dynamic_segments
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def refresh_segments(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await refresh_all_dynamic_segments(session)
        return {"segments_refreshed": count}

    return await run_scheduled_job(
        job_type="segments.refresh_all_dynamic",
        queue_name="campaigns",
        func=_run,
        max_attempts=3,
        timeout_seconds=300,
    )


async def sync_campaigns(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await sync_all_running_campaigns(session)
        return {"campaigns_synced": count}

    return await run_scheduled_job(
        job_type="campaigns.sync_running",
        queue_name="campaigns",
        func=_run,
        max_attempts=3,
        timeout_seconds=300,
    )
