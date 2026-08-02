"""Admin read surface over `OutboxEvent` — the "domain event / outbox log"
Phase 15's `event_log.view` permission covers. Claiming/dispatching stays
in `app.event_bus.dispatcher`."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent


async def list_outbox_events(
    session: AsyncSession,
    *,
    status: str | None = None,
    event_type: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[OutboxEvent], int]:
    conditions = []
    if status is not None:
        conditions.append(OutboxEvent.status == status)
    if event_type is not None:
        conditions.append(OutboxEvent.event_type == event_type)

    total = await session.scalar(select(func.count()).select_from(OutboxEvent).where(*conditions))
    rows = (
        await session.scalars(
            select(OutboxEvent)
            .where(*conditions)
            .order_by(OutboxEvent.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).all()
    return list(rows), total or 0
