"""Shared helper every cron-triggered task in `worker.tasks` uses.

ARQ's `cron_jobs` has no leader election: if apps/worker is ever scaled to
more than one replica, every replica independently fires the same cron tick
at the same wall-clock time. `app.jobs.locks.advisory_lock` (Postgres
session-level `pg_try_advisory_lock`, keyed by job type) is the guard
against a business function actually running twice for one tick — a
replica that loses the race treats that as a normal no-op, not a failure,
since another replica is already handling it. The winning replica's run is
then tracked through `app.jobs.runner.run_job`'s durable `JobRecord`
bookkeeping, exactly as `app/jobs/locks.py`'s own docstring describes this
composition.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from app.jobs.errors import LockNotAcquiredError
from app.jobs.locks import advisory_lock
from app.jobs.runner import run_job
from sqlalchemy.ext.asyncio import AsyncSession

from worker.db import session_scope
from worker.logging import get_logger

logger = get_logger(__name__)


async def run_scheduled_job(
    *,
    job_type: str,
    queue_name: str,
    func: Callable[[AsyncSession], Awaitable[dict[str, Any]]],
    max_attempts: int = 3,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    async with session_scope() as session:
        try:
            async with advisory_lock(session, key=f"cron:{job_type}"):

                async def _execute() -> dict[str, Any]:
                    return await func(session)

                job = await run_job(
                    session,
                    job_type=job_type,
                    trigger="cron",
                    queue_name=queue_name,
                    func=_execute,
                    max_attempts=max_attempts,
                    timeout_seconds=timeout_seconds,
                )
                return dict(job.result) if job.result else {}
        except LockNotAcquiredError:
            logger.info("scheduled_job_skipped_locked", job_type=job_type)
            return {"skipped": "locked"}
