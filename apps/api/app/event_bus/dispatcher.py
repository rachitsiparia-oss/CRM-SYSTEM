"""The outbox dispatcher — INTEGRATIONS_AUTOMATIONS_REALTIME.md section 9.
Claims pending `outbox_events` rows with `SELECT ... FOR UPDATE SKIP
LOCKED` (section 9.5's "workers claim rows atomically... parallel workers
must not publish the same event concurrently"), routes each to its
registered consumer (falling back to `default_audit_consumer` when none is
registered), and records the outcome with bounded retry and
dead-lettering — the same shape `app.jobs.runner.run_job` uses for
JobRecord, applied to OutboxEvent instead.

Four event types (`reservation.created`, `reservation.status_changed`,
`order.created`, `order.status_changed`) are deliberately excluded here:
`app.communications.integrations.process_pending_communication_events`
(Phase 10) already claims and processes those directly against the same
table. Having this generic dispatcher also claim them would race two
independent consumers over the same rows — excluded, not migrated, to
avoid touching that already-tested Phase 10 code path in this phase.
"""

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent
from app.dead_letter.service import create_entry
from app.event_bus.consumers import default_audit_consumer
from app.event_bus.registry import get_consumer
from app.jobs.classify import classify_error, compute_next_retry_at

EXCLUDED_EVENT_TYPES = frozenset(
    {
        "reservation.created",
        "reservation.status_changed",
        "order.created",
        "order.status_changed",
    }
)


async def dispatch_pending_events(
    session: AsyncSession,
    *,
    worker_id: str,
    batch_size: int = 20,
    max_attempts: int = 5,
) -> dict[str, int]:
    now = datetime.now(UTC)
    stmt = (
        select(OutboxEvent)
        .where(
            OutboxEvent.status == "pending",
            OutboxEvent.available_at <= now,
            OutboxEvent.event_type.not_in(EXCLUDED_EVENT_TYPES),
        )
        .order_by(OutboxEvent.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    claimed = list((await session.scalars(stmt)).all())
    for event in claimed:
        event.status = "processing"
        event.locked_by = worker_id
        event.locked_at = now
    await session.flush()
    await session.commit()

    counts = {"published": 0, "failed_retryable": 0, "dead_lettered": 0}
    for event in claimed:
        await _process_one(session, event, max_attempts=max_attempts)
        outcome = "dead_lettered" if event.status == "failed_permanent" else event.status
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


async def _process_one(session: AsyncSession, event: OutboxEvent, *, max_attempts: int) -> None:
    consumer = get_consumer(event.event_type) or default_audit_consumer
    event.attempts += 1
    structlog.contextvars.bind_contextvars(
        outbox_event_id=str(event.id), event_type=event.event_type
    )
    # Committed before the consumer runs (matching `app.jobs.runner.run_job`'s
    # own attempts-then-commit-then-try shape) so that if the consumer fails
    # and this function rolls back, `event.attempts` — durably persisted
    # already — reads back correctly after the rollback expires it, instead
    # of reverting to its pre-increment value.
    await session.flush()
    await session.commit()
    try:
        await consumer(session, event)
    except Exception as exc:
        await session.rollback()
        category = classify_error(exc)
        exhausted = event.attempts >= max_attempts
        event.status = (
            "failed_permanent" if (category == "permanent" or exhausted) else ("failed_retryable")
        )
        event.last_error = str(exc)[:2000]
        if event.status == "failed_retryable":
            event.available_at = compute_next_retry_at(event.attempts)
            event.locked_by = None
            event.locked_at = None
        await session.flush()
        await session.commit()

        if event.status == "failed_permanent":
            await create_entry(
                session,
                source_type="outbox_event",
                source_id=event.id,
                original_type=event.event_type,
                correlation_id=None,
                failure_category=category,
                final_error_summary=event.last_error,
                attempt_history=[
                    {"attempt": event.attempts, "category": category, "error": event.last_error}
                ],
                payload_reference={"aggregate_type": event.aggregate_type},
            )
            await session.commit()
    else:
        event.status = "published"
        event.completed_at = datetime.now(UTC)
        await session.flush()
        await session.commit()
    finally:
        structlog.contextvars.unbind_contextvars("outbox_event_id", "event_type")


def worker_id() -> str:
    """A stable-enough identifier for `locked_by` — not used for
    correctness (the `FOR UPDATE SKIP LOCKED` claim is what prevents
    double-processing), only for operator visibility into which process
    last touched a row."""
    return f"worker-{uuid.uuid4().hex[:12]}"
