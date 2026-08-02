"""Tests for `app.dead_letter` — the resolution workflow
(new -> investigating -> replay_ready -> replayed / ignored_with_reason)
and `replay_entry`'s reset-to-pending behavior
(INTEGRATIONS_AUTOMATIONS_REALTIME.md section 12)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from app.db.models import JobRecord, StaffUser
from app.dead_letter.errors import ReplayNotEligibleError
from app.dead_letter.service import (
    create_entry,
    ignore_entry,
    list_dead_letter_entries,
    mark_investigating,
    mark_replay_ready,
    replay_entry,
)
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def _make_failed_job(session: AsyncSession) -> JobRecord:
    job = JobRecord(
        job_type="test.dead_letter_source",
        trigger="manual",
        queue_name="maintenance",
        status="failed_permanent",
        attempts=1,
    )
    session.add(job)
    await session.flush()
    return job


async def test_replay_entry_rejects_an_entry_not_marked_replay_ready(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    job = await _make_failed_job(db_session)
    entry = await create_entry(
        db_session,
        source_type="job",
        source_id=job.id,
        original_type=job.job_type,
        correlation_id=None,
        failure_category="permanent",
        final_error_summary="boom",
    )
    with pytest.raises(ReplayNotEligibleError):
        await replay_entry(db_session, entry=entry, actor=actor)


async def test_full_resolution_workflow_resets_source_job_to_pending(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    job = await _make_failed_job(db_session)
    entry = await create_entry(
        db_session,
        source_type="job",
        source_id=job.id,
        original_type=job.job_type,
        correlation_id=None,
        failure_category="permanent",
        final_error_summary="boom",
    )
    assert entry.resolution_status == "new"

    entry = await mark_investigating(db_session, entry=entry, actor=actor)
    assert entry.resolution_status == "investigating"

    entry = await mark_replay_ready(db_session, entry=entry, actor=actor, notes="root cause fixed")
    assert entry.resolution_status == "replay_ready"
    assert entry.replay_eligible is True

    await replay_entry(db_session, entry=entry, actor=actor)
    assert entry.resolution_status == "replayed"
    assert entry.replay_actor_id == actor.id

    await db_session.refresh(job)
    assert job.status == "pending"
    assert job.failure_category is None


async def test_ignore_entry_records_a_reason_and_stays_non_replayable(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    job = await _make_failed_job(db_session)
    entry = await create_entry(
        db_session,
        source_type="job",
        source_id=job.id,
        original_type=job.job_type,
        correlation_id=None,
        failure_category="permanent",
        final_error_summary="boom",
    )
    entry = await ignore_entry(db_session, entry=entry, actor=actor, reason="known false positive")
    assert entry.resolution_status == "ignored_with_reason"
    assert entry.replay_eligible is False
    assert entry.notes == "known false positive"


async def test_list_dead_letter_entries_filters_by_resolution_status(
    db_session: AsyncSession,
) -> None:
    job = await _make_failed_job(db_session)
    await create_entry(
        db_session,
        source_type="job",
        source_id=job.id,
        original_type=job.job_type,
        correlation_id=None,
        failure_category="permanent",
        final_error_summary="boom",
    )
    rows, total = await list_dead_letter_entries(db_session, resolution_status="new")
    assert total >= 1
    assert all(r.resolution_status == "new" for r in rows)
