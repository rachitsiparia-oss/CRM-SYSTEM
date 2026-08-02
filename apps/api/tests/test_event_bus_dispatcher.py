"""Tests for `app.event_bus.dispatcher` — claiming, publishing, exclusion
of Phase 10-owned event types, and dead-lettering on exhaustion
(INTEGRATIONS_AUTOMATIONS_REALTIME.md section 9)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.db.models import DeadLetterEntry, OutboxEvent
from app.event_bus.dispatcher import EXCLUDED_EVENT_TYPES, dispatch_pending_events
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _pending_event(event_type: str, *, aggregate_type: str = "test_aggregate") -> OutboxEvent:
    return OutboxEvent(
        id=uuid.uuid4(),
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=uuid.uuid4(),
        payload={"note": "test"},
        status="pending",
        available_at=datetime.now(UTC),
    )


async def test_dispatch_publishes_pending_event_via_default_consumer(
    db_session: AsyncSession,
) -> None:
    event = _pending_event("test.unregistered_event_type")
    db_session.add(event)
    await db_session.flush()

    # A large batch_size guarantees this freshly-inserted event (sorted
    # last by created_at) is claimed regardless of how large the dev
    # database's real pre-existing pending backlog happens to be — the
    # SAVEPOINT this fixture wraps everything in rolls all of it back
    # afterward, so draining the real backlog here has no lasting effect.
    counts = await dispatch_pending_events(db_session, worker_id="test-worker", batch_size=1000)
    assert counts["published"] >= 1

    reloaded = await db_session.scalar(select(OutboxEvent).where(OutboxEvent.id == event.id))
    assert reloaded is not None
    assert reloaded.status == "published"
    assert reloaded.completed_at is not None


async def test_dispatch_never_claims_excluded_event_types(db_session: AsyncSession) -> None:
    excluded_type = next(iter(EXCLUDED_EVENT_TYPES))
    event = _pending_event(excluded_type)
    db_session.add(event)
    await db_session.flush()

    await dispatch_pending_events(db_session, worker_id="test-worker")

    reloaded = await db_session.scalar(select(OutboxEvent).where(OutboxEvent.id == event.id))
    assert reloaded is not None
    assert reloaded.status == "pending"  # untouched — Phase 10's own consumer owns this type


async def test_dispatch_dead_letters_a_permanently_failing_event(db_session: AsyncSession) -> None:
    from app.event_bus.registry import register_consumer

    event_type = f"test.always_fails.{uuid.uuid4().hex[:8]}"

    @register_consumer(event_type)
    async def _always_fails(session: AsyncSession, evt: OutboxEvent) -> None:
        raise ValueError("simulated permanent consumer failure")

    event = _pending_event(event_type)
    db_session.add(event)
    await db_session.flush()

    counts = await dispatch_pending_events(
        db_session, worker_id="test-worker", batch_size=1000, max_attempts=1
    )
    assert counts["dead_lettered"] >= 1

    reloaded = await db_session.scalar(select(OutboxEvent).where(OutboxEvent.id == event.id))
    assert reloaded is not None
    assert reloaded.status == "failed_permanent"

    entry = await db_session.scalar(
        select(DeadLetterEntry).where(DeadLetterEntry.source_id == event.id)
    )
    assert entry is not None
    assert entry.source_type == "outbox_event"
