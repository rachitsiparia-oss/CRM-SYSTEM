"""Thin helper around the Phase 2 `outbox_events` table —
DATABASE_AND_API.md section 16.6, ARCHITECTURE_AND_TECH_STACK.md section
12.4. Every Phase 5 domain event listed in
INTEGRATIONS_AUTOMATIONS_REALTIME.md section 8.1 (customer.created,
customer.updated, customer.merged, lead.created, lead.stage_changed) is
recorded here, in the same transaction as the state change it describes —
no other outbox mechanism is introduced.

There is no consumer/dispatcher wired up for these events yet (that is
worker/integration infrastructure outside Phase 5's scope); rows sit in
`pending` status, which is correct and safe — CLAUDE.md section 14 ("Do
not create events with no consumer unless they are explicitly part of the
domain-event contract and documented"). These five are documented.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent


async def record_domain_event(
    session: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    payload: dict[str, Any],
) -> None:
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
        status="pending",
        available_at=datetime.now(UTC),
    )
    session.add(event)
    await session.flush()
