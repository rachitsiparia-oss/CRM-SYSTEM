"""Operational data retention — the Phase 15 scheduler's "cleanup jobs"
catalog entry. Only prunes short-lived, machine-generated tracking rows
whose value is fully captured elsewhere once terminal: a `succeeded`
JobRecord's effect already landed in whatever business row it touched, and
a `published` OutboxEvent's effect already landed via its consumer. Rows
that still carry unresolved information (`failed_permanent` — mirrored in
a `DeadLetterEntry` for triage) are never purged here; dead-letter rows
have their own lifecycle via `app.dead_letter`.

Deliberately does not touch `audit_log`, inventory/loyalty ledgers, order
history, or any other durable business-history table — CLAUDE.md section 7
requires those to remain permanent and append-oriented; this module only
ever targets ops/observability bookkeeping tables.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobRecord, OutboxEvent

_JOB_RECORD_RETENTION_DAYS = 90
_OUTBOX_EVENT_RETENTION_DAYS = 90
_PURGEABLE_JOB_STATUSES = ("succeeded", "cancelled")
_PURGEABLE_OUTBOX_STATUSES = ("published", "cancelled")


async def purge_stale_operational_records(
    session: AsyncSession, *, now: datetime | None = None
) -> dict[str, int]:
    now = now or datetime.now(UTC)
    job_cutoff = now - timedelta(days=_JOB_RECORD_RETENTION_DAYS)
    outbox_cutoff = now - timedelta(days=_OUTBOX_EVENT_RETENTION_DAYS)

    job_result = await session.execute(
        delete(JobRecord).where(
            JobRecord.status.in_(_PURGEABLE_JOB_STATUSES),
            JobRecord.completed_at.is_not(None),
            JobRecord.completed_at < job_cutoff,
        )
    )
    outbox_result = await session.execute(
        delete(OutboxEvent).where(
            OutboxEvent.status.in_(_PURGEABLE_OUTBOX_STATUSES),
            OutboxEvent.completed_at.is_not(None),
            OutboxEvent.completed_at < outbox_cutoff,
        )
    )
    return {
        "job_records_purged": cast(CursorResult[Any], job_result).rowcount or 0,
        "outbox_events_purged": cast(CursorResult[Any], outbox_result).rowcount or 0,
    }
