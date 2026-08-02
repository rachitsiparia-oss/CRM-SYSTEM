from typing import Any

from app.staff_operations.reminders import (
    dispatch_certification_expiry_reminders,
    dispatch_knowledge_acknowledgement_reminders,
    dispatch_training_overdue_reminders,
)
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def send_certification_expiry_reminders(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await dispatch_certification_expiry_reminders(session)
        return {"reminders_sent": count}

    return await run_scheduled_job(
        job_type="staff.certification_expiry_reminders",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )


async def send_training_overdue_reminders(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await dispatch_training_overdue_reminders(session)
        return {"reminders_sent": count}

    return await run_scheduled_job(
        job_type="staff.training_overdue_reminders",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )


async def send_knowledge_acknowledgement_reminders(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        count = await dispatch_knowledge_acknowledgement_reminders(session)
        return {"reminders_sent": count}

    return await run_scheduled_job(
        job_type="knowledge.acknowledgement_reminders",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )
