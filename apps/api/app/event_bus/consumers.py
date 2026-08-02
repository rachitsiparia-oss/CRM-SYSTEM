"""Default consumer — every outbox event that has no domain-specific
consumer registered still gets this one, so "the event was durably
published" is always observable (INTEGRATIONS_AUTOMATIONS_REALTIME.md
section 24.1's required "outbox publication" log), without inventing an
unspecified business reaction for event types no document assigns one to.
This is a real, useful consumer — a structured audit trail of every domain
event the system has produced — not a placeholder.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import OutboxEvent

logger = get_logger(__name__)


async def default_audit_consumer(session: AsyncSession, event: OutboxEvent) -> None:
    logger.info(
        "outbox_event_published",
        event_id=str(event.id),
        event_type=event.event_type,
        aggregate_type=event.aggregate_type,
        aggregate_id=str(event.aggregate_id),
    )
