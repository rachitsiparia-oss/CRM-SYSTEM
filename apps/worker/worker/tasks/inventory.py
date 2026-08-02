from typing import Any

from app.inventory.alerts import dispatch_low_stock_alerts
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def send_low_stock_alerts(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await dispatch_low_stock_alerts(session)
        return {"alerts_sent": count}

    return await run_scheduled_job(
        job_type="inventory.low_stock_alerts",
        queue_name="critical-domain",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )
