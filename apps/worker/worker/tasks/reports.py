from typing import Any

from app.forecasts.service import run_all_active_forecasts
from app.report_schedules.service import run_due_scheduled_reports
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def run_scheduled_reports(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        return dict(await run_due_scheduled_reports(session))

    return await run_scheduled_job(
        job_type="report_schedules.run_due",
        queue_name="reports",
        func=_run,
        max_attempts=3,
        timeout_seconds=300,
    )


async def run_forecasts(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await run_all_active_forecasts(session)
        return {"forecasts_run": count}

    return await run_scheduled_job(
        job_type="forecasts.run_all_active",
        queue_name="reports",
        func=_run,
        max_attempts=3,
        timeout_seconds=300,
    )
