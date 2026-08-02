from typing import Any

from app.communications.integrations import process_pending_communication_events
from app.event_bus.dispatcher import dispatch_pending_events, worker_id
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def dispatch_outbox_events(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        return dict(await dispatch_pending_events(session, worker_id=worker_id()))

    return await run_scheduled_job(
        job_type="event_bus.dispatch_pending",
        queue_name="critical-domain",
        func=_run,
        max_attempts=3,
        timeout_seconds=120,
    )


async def dispatch_communication_events(ctx: dict[str, Any]) -> dict[str, Any]:
    """The Phase 10 reservation/order communication-event consumer
    (`app.communications.integrations`) — excluded from the generic
    `dispatch_pending_events` above to avoid two consumers racing over the
    same rows (see `app.event_bus.dispatcher`'s `EXCLUDED_EVENT_TYPES`
    docstring), but never itself wired to a scheduler before this phase."""

    async def _run(session: AsyncSession) -> dict[str, Any]:
        return dict(await process_pending_communication_events(session))

    return await run_scheduled_job(
        job_type="communications.dispatch_events",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=120,
    )
