"""Consumer registry — the decoupling mechanism
INTEGRATIONS_AUTOMATIONS_REALTIME.md section 8 asks for ("every module
publishes domain events; consumers subscribe without tight coupling").
A consumer registers itself against an `event_type` string; the dispatcher
(`app.event_bus.dispatcher`) never imports a specific domain module — it
only looks the event type up here. Future phases add consumers by calling
`register_consumer` from their own module, never by editing the dispatcher.
"""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent

Consumer = Callable[[AsyncSession, OutboxEvent], Awaitable[None]]

_CONSUMERS: dict[str, Consumer] = {}


def register_consumer(event_type: str) -> Callable[[Consumer], Consumer]:
    def decorator(func: Consumer) -> Consumer:
        _CONSUMERS[event_type] = func
        return func

    return decorator


def get_consumer(event_type: str) -> Consumer | None:
    return _CONSUMERS.get(event_type)
