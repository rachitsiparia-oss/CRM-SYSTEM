"""Scheduled-message dispatch and message retry — both existed as
callable engine functions since Phase 10 but, like several other Phase
10/11 functions, were never wired to a scheduler before this phase."""

from typing import Any

from app.communications.scheduling import process_due_scheduled_messages, retry_all_failed_messages
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def process_scheduled_messages(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        processed = await process_due_scheduled_messages(session)
        return {"processed": len(processed)}

    return await run_scheduled_job(
        job_type="communications.process_scheduled_messages",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )


async def retry_failed_messages(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await retry_all_failed_messages(session)
        return {"retried": count}

    return await run_scheduled_job(
        job_type="communications.retry_failed_messages",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )
