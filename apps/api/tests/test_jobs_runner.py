"""Tests for `app.jobs.runner` — the durable `JobRecord` wrapper every
scheduled/on-demand job in apps/worker goes through. Covers success,
retryable-vs-permanent failure classification, idempotency-key reuse, and
dead-letter creation on exhaustion (INTEGRATIONS_AUTOMATIONS_REALTIME.md
sections 10-12)."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import DeadLetterEntry, JobRecord, StaffUser
from app.jobs.errors import JobNotFoundError
from app.jobs.runner import cancel_job, run_job
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def test_run_job_success_records_result(db_session: AsyncSession) -> None:
    async def _ok() -> dict[str, Any]:
        return {"processed": 3}

    job = await run_job(
        db_session,
        job_type="test.success",
        trigger="manual",
        queue_name="maintenance",
        func=_ok,
    )
    assert job.status == "succeeded"
    assert job.result == {"processed": 3}
    assert job.attempts == 1
    assert job.completed_at is not None


async def test_run_job_permanent_failure_dead_letters_on_exhaustion(
    db_session: AsyncSession,
) -> None:
    async def _fail() -> dict[str, Any]:
        raise ValueError("deliberately unrecoverable")

    with pytest.raises(ValueError):
        await run_job(
            db_session,
            job_type="test.permanent_failure",
            trigger="manual",
            queue_name="maintenance",
            func=_fail,
            max_attempts=1,
        )

    job = await db_session.scalar(
        select(JobRecord).where(JobRecord.job_type == "test.permanent_failure")
    )
    assert job is not None
    assert job.status == "failed_permanent"
    assert job.failure_category == "permanent"

    entry = await db_session.scalar(
        select(DeadLetterEntry).where(DeadLetterEntry.source_id == job.id)
    )
    assert entry is not None
    assert entry.source_type == "job"
    assert entry.resolution_status == "new"


async def test_run_job_retryable_failure_schedules_retry_without_dead_letter(
    db_session: AsyncSession,
) -> None:
    async def _fail() -> dict[str, Any]:
        raise ConnectionError("transient network blip")

    with pytest.raises(ConnectionError):
        await run_job(
            db_session,
            job_type="test.retryable_failure",
            trigger="manual",
            queue_name="maintenance",
            func=_fail,
            max_attempts=3,
        )

    job = await db_session.scalar(
        select(JobRecord).where(JobRecord.job_type == "test.retryable_failure")
    )
    assert job is not None
    assert job.status == "retry_wait"
    assert job.failure_category == "retryable"
    assert job.next_retry_at is not None

    entry = await db_session.scalar(
        select(DeadLetterEntry).where(DeadLetterEntry.source_id == job.id)
    )
    assert entry is None


async def test_run_job_timeout_is_classified_retryable(db_session: AsyncSession) -> None:
    import asyncio

    async def _hang() -> dict[str, Any]:
        await asyncio.sleep(5)
        return {"never": "reached"}

    with pytest.raises(TimeoutError):
        await run_job(
            db_session,
            job_type="test.timeout",
            trigger="manual",
            queue_name="maintenance",
            func=_hang,
            max_attempts=3,
            timeout_seconds=1,
        )

    job = await db_session.scalar(select(JobRecord).where(JobRecord.job_type == "test.timeout"))
    assert job is not None
    assert job.status == "retry_wait"
    assert job.failure_category == "retryable"
    assert job.next_retry_at is not None


async def test_run_job_idempotency_key_reuses_succeeded_row_without_rerunning(
    db_session: AsyncSession,
) -> None:
    call_count = 0
    key = f"idem-{uuid.uuid4().hex[:8]}"

    async def _count_calls() -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        return {"calls": call_count}

    first = await run_job(
        db_session,
        job_type="test.idempotent",
        trigger="manual",
        queue_name="maintenance",
        func=_count_calls,
        idempotency_key=key,
    )
    second = await run_job(
        db_session,
        job_type="test.idempotent",
        trigger="manual",
        queue_name="maintenance",
        func=_count_calls,
        idempotency_key=key,
    )
    assert first.id == second.id
    assert call_count == 1
    assert second.result == {"calls": 1}


async def test_cancel_job_marks_pending_job_cancelled(db_session: AsyncSession) -> None:
    job = JobRecord(
        job_type="test.cancel_me",
        trigger="manual",
        queue_name="maintenance",
        status="pending",
        attempts=0,
    )
    db_session.add(job)
    await db_session.flush()

    cancelled = await cancel_job(db_session, job_id=job.id)
    assert cancelled.status == "cancelled"
    assert cancelled.completed_at is not None


async def test_cancel_job_raises_for_unknown_id(db_session: AsyncSession) -> None:
    with pytest.raises(JobNotFoundError):
        await cancel_job(db_session, job_id=uuid.uuid4())
