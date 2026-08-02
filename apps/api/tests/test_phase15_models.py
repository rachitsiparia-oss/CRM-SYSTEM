"""Constraint tests for Phase 15's new tables/columns — check constraints
must actually reject invalid values, not just document them
(DATABASE_AND_API.md section 12's "use check constraints for valid
values"). `JobRecord.status`/defaults are already covered in
test_db_foundation.py; this file covers the columns Phase 15 added."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.db.models import (
    DeadLetterEntry,
    FeatureFlag,
    Integration,
    JobRecord,
    Notification,
    NotificationDeliveryAttempt,
    OperationalSettings,
    StaffUser,
)
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def test_job_record_rejects_invalid_queue_name(db_session: AsyncSession) -> None:
    job = JobRecord(
        job_type="test.job", trigger="manual", queue_name="not_a_real_queue", priority="normal"
    )
    db_session.add(job)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_job_record_rejects_invalid_priority(db_session: AsyncSession) -> None:
    job = JobRecord(
        job_type="test.job", trigger="manual", queue_name="maintenance", priority="urgent-ish"
    )
    db_session.add(job)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_job_record_queue_name_and_priority_default(db_session: AsyncSession) -> None:
    job = JobRecord(job_type="test.job", trigger="manual")
    db_session.add(job)
    await db_session.flush()
    assert job.queue_name == "maintenance"
    assert job.priority == "normal"


async def test_integration_rejects_invalid_category(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    integration = Integration(
        code=f"test-{uuid.uuid4().hex[:8]}",
        category="not_a_real_category",
        provider_code="test",
        display_name="Test",
        created_by=actor.id,
        updated_by=actor.id,
    )
    db_session.add(integration)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_integration_code_is_unique(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    code = f"test-{uuid.uuid4().hex[:8]}"
    db_session.add(
        Integration(
            code=code,
            category="email",
            provider_code="test",
            display_name="Test",
            created_by=actor.id,
            updated_by=actor.id,
        )
    )
    await db_session.flush()
    db_session.add(
        Integration(
            code=code,
            category="sms",
            provider_code="test-2",
            display_name="Test 2",
            created_by=actor.id,
            updated_by=actor.id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_feature_flag_code_is_unique(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    code = f"test.flag.{uuid.uuid4().hex[:8]}"
    db_session.add(FeatureFlag(code=code, name="A", created_by=actor.id, updated_by=actor.id))
    await db_session.flush()
    db_session.add(FeatureFlag(code=code, name="B", created_by=actor.id, updated_by=actor.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_dead_letter_entry_rejects_invalid_source_type(db_session: AsyncSession) -> None:
    entry = DeadLetterEntry(
        source_type="bogus",  # must still fit source_type's VARCHAR(16) column
        source_id=uuid.uuid4(),
        original_type="test.job",
    )
    db_session.add(entry)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_operational_settings_singleton_guard_rejects_second_row(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    # A seeded dev database already has the real singleton row; clear it
    # first (inside this test's own rolled-back SAVEPOINT) so the first
    # insert below is genuinely the first row, not a second one.
    await db_session.execute(delete(OperationalSettings))
    db_session.add(OperationalSettings(created_by=actor.id, updated_by=actor.id))
    await db_session.flush()
    db_session.add(OperationalSettings(created_by=actor.id, updated_by=actor.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_operational_settings_rejects_non_positive_worker_max_jobs(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    db_session.add(OperationalSettings(created_by=actor.id, updated_by=actor.id, worker_max_jobs=0))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_notification_delivery_attempt_rejects_invalid_channel(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    notification = Notification(
        notification_type="test.notification",
        title="Test",
        recipient_staff_id=actor.id,
    )
    db_session.add(notification)
    await db_session.flush()

    attempt = NotificationDeliveryAttempt(notification_id=notification.id, channel="carrier_pigeon")
    db_session.add(attempt)
    with pytest.raises(IntegrityError):
        await db_session.flush()
