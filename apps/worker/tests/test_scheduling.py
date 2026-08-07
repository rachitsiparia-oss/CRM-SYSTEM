"""Tests for `worker.scheduling.run_scheduled_job` — the advisory-lock +
`app.jobs.runner.run_job` composition every cron task in `worker.tasks`
goes through. Runs against the real dev database via `worker.db.session_scope`
(this project has no SAVEPOINT-based test fixture yet); each test cleans up
the `JobRecord` row it creates so nothing real is left behind.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from app.db.models import JobRecord
from app.jobs.locks import advisory_lock
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from worker.config import get_worker_settings
from worker.db import session_scope
from worker.scheduling import run_scheduled_job

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not get_worker_settings().database_url,
        reason="DATABASE_URL not configured — see apps/api/tests/conftest.py's "
        "identical skip-not-fail convention (CLAUDE.md section 21)",
    ),
]


async def _cleanup(job_type: str) -> None:
    async with session_scope() as session:
        await session.execute(delete(JobRecord).where(JobRecord.job_type == job_type))


async def test_run_scheduled_job_executes_and_records_success() -> None:
    job_type = f"test.scheduling.{uuid.uuid4().hex[:8]}"
    try:

        async def _run(session: AsyncSession) -> dict[str, Any]:
            return {"ran": True}

        result = await run_scheduled_job(
            job_type=job_type, queue_name="maintenance", func=_run, max_attempts=1
        )
        assert result == {"ran": True}

        async with session_scope() as session:
            job = await session.scalar(select(JobRecord).where(JobRecord.job_type == job_type))
            assert job is not None
            assert job.status == "succeeded"
    finally:
        await _cleanup(job_type)


async def test_run_scheduled_job_skips_when_lock_already_held() -> None:
    job_type = f"test.scheduling.locked.{uuid.uuid4().hex[:8]}"
    try:
        async with (
            session_scope() as holder_session,
            advisory_lock(holder_session, key=f"cron:{job_type}"),
        ):
            call_count = 0

            async def _run(session: AsyncSession) -> dict[str, Any]:
                nonlocal call_count
                call_count += 1
                return {"ran": True}

            result = await run_scheduled_job(
                job_type=job_type, queue_name="maintenance", func=_run, max_attempts=1
            )
            assert result == {"skipped": "locked"}
            assert call_count == 0
    finally:
        await _cleanup(job_type)
