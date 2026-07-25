import uuid
from datetime import UTC, datetime

import pytest
from app.db.models import AuditEvent, JobRecord, OutboxEvent
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_audit_event_generates_id_and_created_at(db_session: AsyncSession) -> None:
    event = AuditEvent(
        actor_id=uuid.uuid4(),
        action_code="customer.merge",
        target_type="customer",
        target_id=uuid.uuid4(),
        source="api",
    )
    db_session.add(event)
    await db_session.flush()

    assert event.id is not None
    assert event.created_at is not None


async def test_outbox_event_defaults_to_pending(db_session: AsyncSession) -> None:
    event = OutboxEvent(
        event_type="order.created.v1",
        aggregate_type="order",
        aggregate_id=uuid.uuid4(),
        payload={"order_number": "ORD-0001"},
        available_at=datetime.now(UTC),
    )
    db_session.add(event)
    await db_session.flush()

    assert event.status == "pending"
    assert event.attempts == 0


async def test_outbox_event_rejects_invalid_status(db_session: AsyncSession) -> None:
    event = OutboxEvent(
        event_type="order.created.v1",
        aggregate_type="order",
        aggregate_id=uuid.uuid4(),
        payload={},
        status="not_a_real_status",
        available_at=datetime.now(UTC),
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_outbox_event_idempotency_key_is_unique(db_session: AsyncSession) -> None:
    key = f"test-{uuid.uuid4()}"
    db_session.add(
        OutboxEvent(
            event_type="order.created.v1",
            aggregate_type="order",
            aggregate_id=uuid.uuid4(),
            payload={},
            available_at=datetime.now(UTC),
            idempotency_key=key,
        )
    )
    await db_session.flush()

    db_session.add(
        OutboxEvent(
            event_type="order.created.v1",
            aggregate_type="order",
            aggregate_id=uuid.uuid4(),
            payload={},
            available_at=datetime.now(UTC),
            idempotency_key=key,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_job_record_rejects_invalid_status(db_session: AsyncSession) -> None:
    job = JobRecord(job_type="send_reservation_reminder", trigger="scheduled", status="bogus")
    db_session.add(job)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_job_record_defaults(db_session: AsyncSession) -> None:
    job = JobRecord(job_type="send_reservation_reminder", trigger="scheduled")
    db_session.add(job)
    await db_session.flush()

    assert job.status == "scheduled"
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.timeout_seconds == 300
