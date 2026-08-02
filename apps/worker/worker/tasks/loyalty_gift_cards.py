from typing import Any

from app.gift_cards.service import expire_due_gift_cards
from app.loyalty.expiry import expire_due_points
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def expire_loyalty_points(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await expire_due_points(session)
        return {"accounts_expired": count}

    return await run_scheduled_job(
        job_type="loyalty.expire_due_points",
        queue_name="campaigns",
        func=_run,
        max_attempts=3,
        timeout_seconds=300,
    )


async def expire_gift_cards(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await expire_due_gift_cards(session)
        return {"gift_cards_expired": count}

    return await run_scheduled_job(
        job_type="gift_cards.expire_due",
        queue_name="campaigns",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )
