from typing import Any

from app.jobs.retention import purge_stale_operational_records
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def purge_stale_records(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        return dict(await purge_stale_operational_records(session))

    return await run_scheduled_job(
        job_type="maintenance.purge_stale_records",
        queue_name="maintenance",
        func=_run,
        max_attempts=2,
        timeout_seconds=300,
    )
