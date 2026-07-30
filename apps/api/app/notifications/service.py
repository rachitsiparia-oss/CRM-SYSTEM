"""Notification creation and read/dismiss/action state transitions.
DATABASE_AND_API.md section 16.4, extended per this phase's own instruction
(dedup, priority, dismissed/actioned state) — see the Phase 10 deviations
note for the full accounting.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification


async def notify(
    session: AsyncSession,
    *,
    notification_type: str,
    title: str,
    recipient_staff_id: uuid.UUID,
    body: str | None = None,
    priority: str = "normal",
    record_type: str | None = None,
    record_id: uuid.UUID | None = None,
    dedup_key: str | None = None,
) -> Notification | None:
    """Returns `None` (no-op) when `dedup_key` collides with an existing
    notification — CLAUDE.md section 15 / this phase's own instruction's
    Definition of Done: "Notifications are deduplicated.\""""
    if dedup_key is not None:
        insert_stmt = (
            pg_insert(Notification)
            .values(
                id=uuid.uuid4(),
                recipient_staff_id=recipient_staff_id,
                notification_type=notification_type,
                title=title,
                body=body,
                priority=priority,
                record_type=record_type,
                record_id=record_id,
                dedup_key=dedup_key,
            )
            .on_conflict_do_nothing(
                index_elements=["dedup_key"], index_where=text("dedup_key IS NOT NULL")
            )
            .returning(Notification.id)
        )
        result = await session.execute(insert_stmt)
        inserted_id = result.scalar_one_or_none()
        if inserted_id is None:
            return None
        await session.flush()
        return await session.get(Notification, inserted_id)

    notification = Notification(
        recipient_staff_id=recipient_staff_id,
        notification_type=notification_type,
        title=title,
        body=body,
        priority=priority,
        record_type=record_type,
        record_id=record_id,
    )
    session.add(notification)
    await session.flush()
    return notification


async def broadcast(
    session: AsyncSession,
    *,
    recipient_staff_ids: list[uuid.UUID],
    title: str,
    body: str | None,
    priority: str = "normal",
) -> list[Notification]:
    notifications = []
    for recipient_id in recipient_staff_ids:
        result = await notify(
            session,
            notification_type="staff.broadcast",
            title=title,
            body=body,
            priority=priority,
            recipient_staff_id=recipient_id,
        )
        if result is not None:
            notifications.append(result)
    return notifications


async def mark_read(session: AsyncSession, *, notification: Notification) -> Notification:
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await session.flush()
    return notification


async def mark_all_read(session: AsyncSession, *, recipient_staff_id: uuid.UUID) -> int:
    unread = (
        await session.scalars(
            select(Notification).where(
                Notification.recipient_staff_id == recipient_staff_id,
                Notification.read_at.is_(None),
            )
        )
    ).all()
    now = datetime.now(UTC)
    for notification in unread:
        notification.read_at = now
    await session.flush()
    return len(unread)


async def dismiss(session: AsyncSession, *, notification: Notification) -> Notification:
    notification.dismissed_at = datetime.now(UTC)
    await session.flush()
    return notification


async def mark_actioned(session: AsyncSession, *, notification: Notification) -> Notification:
    notification.actioned_at = datetime.now(UTC)
    await session.flush()
    return notification
