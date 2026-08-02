"""Typed job execution — wraps a business callable with the durable
`JobRecord` bookkeeping INTEGRATIONS_AUTOMATIONS_REALTIME.md section 10
describes. ARQ/Redis coordinate *execution* (retries, scheduling); this
module is the durable, queryable source of truth for what actually
happened, per TOOLS.md section 7.3 ("PostgreSQL still contains the durable
business job records... ARQ and Redis... are not the sole durable source
of business truth").

Every recurring/cron job and every on-demand ARQ job in `apps/worker`
should call `run_job` rather than writing directly to `JobRecord` — this
is the one place idempotency, retry classification, backoff, and
dead-lettering happen, so every job gets the same guarantees without
reimplementing them.
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobRecord
from app.dead_letter.service import create_entry
from app.jobs.classify import classify_error, compute_next_retry_at


async def run_job(
    session: AsyncSession,
    *,
    job_type: str,
    trigger: str,
    queue_name: str,
    func: Callable[[], Awaitable[dict[str, Any]]],
    priority: str = "normal",
    idempotency_key: str | None = None,
    max_attempts: int = 5,
    timeout_seconds: int = 300,
    correlation_id: str | None = None,
    backoff_base_seconds: int = 30,
    backoff_cap_seconds: int = 1800,
) -> JobRecord:
    """Runs `func()` under `JobRecord` tracking and returns the row.

    Idempotency: when `idempotency_key` is given and an existing row with
    that key already `succeeded`, `func` is never called — the existing
    row is returned as-is (INTEGRATIONS_AUTOMATIONS_REALTIME.md section
    2.7). A non-succeeded existing row (a prior `retry_wait`/
    `failed_permanent` attempt with the same key) is reused and re-run
    rather than duplicated.

    On failure: partial writes `func` may have flushed to `session` are
    rolled back before recording the failure, so a failed job's committed
    state never includes half-applied domain changes. The exception is
    always re-raised afterward so ARQ's own attempt/retry accounting stays
    accurate — `JobRecord` is a record of what happened, not a substitute
    for ARQ's execution retry.
    """
    existing: JobRecord | None = None
    if idempotency_key:
        existing = await session.scalar(
            select(JobRecord).where(JobRecord.idempotency_key == idempotency_key)
        )
        if existing is not None and existing.status == "succeeded":
            return existing

    job = existing or JobRecord(
        job_type=job_type,
        trigger=trigger,
        queue_name=queue_name,
        priority=priority,
        idempotency_key=idempotency_key,
        max_attempts=max_attempts,
        timeout_seconds=timeout_seconds,
        correlation_id=correlation_id,
        # `attempts` has a DB-side `default=0`, but that only applies at
        # INSERT time — a freshly constructed, not-yet-flushed JobRecord
        # has `attempts is None` in Python, and the `+= 1` below needs a
        # real int immediately.
        attempts=0,
    )
    if existing is None:
        session.add(job)

    job.status = "running"
    job.attempts += 1
    job.started_at = datetime.now(UTC)
    job.next_retry_at = None
    await session.flush()
    await session.commit()

    # Bound for the duration of `func()` so every log line any domain
    # service emits while this job runs carries the same job identity —
    # CLAUDE.md section 19's "include correlation or request IDs," applied
    # to background jobs the way `RequestContextMiddleware` applies it to
    # HTTP requests.
    structlog.contextvars.bind_contextvars(
        job_id=str(job.id), job_type=job.job_type, correlation_id=job.correlation_id
    )
    try:
        result = await asyncio.wait_for(func(), timeout=timeout_seconds)
    except Exception as exc:
        await session.rollback()
        category = classify_error(exc)
        exhausted = job.attempts >= job.max_attempts
        job.status = "failed_permanent" if (category == "permanent" or exhausted) else "retry_wait"
        job.failure_category = category
        job.failure_message = str(exc)[:2000]
        if job.status == "retry_wait":
            job.next_retry_at = compute_next_retry_at(
                job.attempts, base_seconds=backoff_base_seconds, cap_seconds=backoff_cap_seconds
            )
        else:
            job.completed_at = datetime.now(UTC)
        await session.flush()
        await session.commit()

        if job.status == "failed_permanent":
            await create_entry(
                session,
                source_type="job",
                source_id=job.id,
                original_type=job.job_type,
                correlation_id=job.correlation_id,
                failure_category=job.failure_category,
                final_error_summary=job.failure_message,
                attempt_history=[
                    {
                        "attempt": job.attempts,
                        "failed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "category": job.failure_category,
                        "error": job.failure_message,
                    }
                ],
            )
            await session.commit()
        raise
    else:
        job.status = "succeeded"
        job.completed_at = datetime.now(UTC)
        job.result = result
        job.progress = None
        await session.flush()
        await session.commit()
        return job
    finally:
        structlog.contextvars.unbind_contextvars("job_id", "job_type", "correlation_id")


async def cancel_job(session: AsyncSession, *, job_id: uuid.UUID) -> JobRecord:
    """Marks a job cancelled — only meaningful for a job still `pending`/
    `scheduled`/`retry_wait`; a `running` job cannot be interrupted
    mid-execution from here (no cross-process cancellation channel exists),
    so this only prevents a *future* retry/run from starting."""
    from app.jobs.errors import JobNotFoundError

    job = await session.get(JobRecord, job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found.")
    if job.status in ("pending", "scheduled", "retry_wait"):
        job.status = "cancelled"
        job.completed_at = datetime.now(UTC)
        await session.flush()
    return job
