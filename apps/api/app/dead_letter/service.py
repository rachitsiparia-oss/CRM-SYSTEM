"""Dead-letter entry creation — INTEGRATIONS_AUTOMATIONS_REALTIME.md
section 12. `create_entry` is called from exactly two places: `app.jobs`
(a job that exhausted its retry budget) and the outbox dispatcher (an
event that exhausted its retry budget). Listing, replay, and resolution
live in this same module (see `list_entries`/`replay_entry`/
`resolve_entry` below) so this stays the single place dead-letter state
transitions happen — no second dead-letter table or code path anywhere
else in the codebase.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeadLetterEntry, JobRecord, OutboxEvent, StaffUser
from app.dead_letter.errors import DeadLetterError, DeadLetterNotFoundError, ReplayNotEligibleError


async def create_entry(
    session: AsyncSession,
    *,
    source_type: str,
    source_id: uuid.UUID,
    original_type: str,
    correlation_id: str | None,
    failure_category: str | None,
    final_error_summary: str | None,
    attempt_history: list[dict[str, Any]] | None = None,
    payload_reference: dict[str, Any] | None = None,
) -> DeadLetterEntry:
    entry = DeadLetterEntry(
        source_type=source_type,
        source_id=source_id,
        original_type=original_type,
        correlation_id=correlation_id,
        failure_category=failure_category,
        final_error_summary=final_error_summary,
        attempt_history=attempt_history,
        payload_reference=payload_reference,
        dead_letter_at=datetime.now(UTC),
        resolution_status="new",
        replay_eligible=False,
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_dead_letter_entry(session: AsyncSession, entry_id: uuid.UUID) -> DeadLetterEntry:
    entry = await session.get(DeadLetterEntry, entry_id)
    if entry is None:
        raise DeadLetterNotFoundError(f"Dead-letter entry {entry_id} not found.")
    return entry


async def list_dead_letter_entries(
    session: AsyncSession,
    *,
    resolution_status: str | None = None,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DeadLetterEntry], int]:
    conditions = []
    if resolution_status:
        conditions.append(DeadLetterEntry.resolution_status == resolution_status)
    if source_type:
        conditions.append(DeadLetterEntry.source_type == source_type)

    count_stmt = select(DeadLetterEntry)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = len((await session.scalars(count_stmt)).all())

    stmt = select(DeadLetterEntry).order_by(DeadLetterEntry.dead_letter_at.desc())
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.limit(limit).offset(offset)
    rows = (await session.scalars(stmt)).all()
    return list(rows), total


async def mark_investigating(
    session: AsyncSession, *, entry: DeadLetterEntry, actor: StaffUser
) -> DeadLetterEntry:
    entry.resolution_status = "investigating"
    entry.updated_by = actor.id
    await session.flush()
    return entry


async def mark_replay_ready(
    session: AsyncSession, *, entry: DeadLetterEntry, actor: StaffUser, notes: str | None = None
) -> DeadLetterEntry:
    """Section 12.3's "corrected root cause" gate — a human explicitly
    marks an entry replay-ready only after fixing whatever caused the
    original failure. `replay_entry` refuses to run against anything else."""
    entry.resolution_status = "replay_ready"
    entry.replay_eligible = True
    entry.owner_staff_id = actor.id
    entry.updated_by = actor.id
    if notes:
        entry.notes = notes
    await session.flush()
    return entry


async def ignore_entry(
    session: AsyncSession, *, entry: DeadLetterEntry, actor: StaffUser, reason: str
) -> DeadLetterEntry:
    entry.resolution_status = "ignored_with_reason"
    entry.replay_eligible = False
    entry.notes = reason
    entry.updated_by = actor.id
    await session.flush()
    return entry


async def replay_entry(session: AsyncSession, *, entry: DeadLetterEntry, actor: StaffUser) -> None:
    """Re-queues the original job/outbox row for re-execution by resetting
    it to a pending state — never re-runs the failed work inline, and
    never bypasses the row's own idempotency key. The next scheduler tick
    or outbox dispatch cycle picks it up exactly like a fresh occurrence.
    """
    if not entry.replay_eligible or entry.resolution_status != "replay_ready":
        raise ReplayNotEligibleError(
            "This entry must be marked replay_ready (corrected root cause confirmed) "
            "before it can be replayed."
        )

    if entry.source_type == "job":
        job = await session.get(JobRecord, entry.source_id)
        if job is None:
            raise DeadLetterError(f"Source job {entry.source_id} no longer exists.")
        job.status = "pending"
        job.next_retry_at = None
        job.failure_category = None
        job.failure_message = None
    elif entry.source_type == "outbox_event":
        event = await session.get(OutboxEvent, entry.source_id)
        if event is None:
            raise DeadLetterError(f"Source outbox event {entry.source_id} no longer exists.")
        event.status = "pending"
        event.available_at = datetime.now(UTC)
        event.locked_by = None
        event.locked_at = None
        event.last_error = None
    else:  # pragma: no cover - source_type is DB-constrained to these two
        raise DeadLetterError(f"Unknown dead-letter source_type {entry.source_type!r}.")

    entry.resolution_status = "replayed"
    entry.replay_actor_id = actor.id
    entry.replay_at = datetime.now(UTC)
    entry.updated_by = actor.id
    await session.flush()
