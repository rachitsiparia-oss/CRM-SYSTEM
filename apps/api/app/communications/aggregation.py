"""Customer/Lead communication statistics for Customer-360 and Lead-detail
integration — this phase's own instruction section 12: "Do not duplicate
existing fields — use read-time aggregation or established projection
patterns (mirrors the Phase 9 Customer-360 pattern already established)."
No new `Customer`/`Lead` columns are added; everything here is computed at
read time from `conversations`/`messages`, exactly like
`app.reservations.customer_stats`.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.schemas import CustomerCommunicationStatsOut
from app.db.models import Conversation, Message


async def get_customer_communication_stats(
    session: AsyncSession, customer_id: uuid.UUID
) -> CustomerCommunicationStatsOut:
    open_count = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.customer_id == customer_id,
            Conversation.status.not_in(("resolved", "closed", "spam")),
        )
    )
    unresolved_count = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.customer_id == customer_id,
            Conversation.status.not_in(("resolved", "closed")),
        )
    )
    last_contact_at = await session.scalar(
        select(func.max(Conversation.last_activity_at)).where(
            Conversation.customer_id == customer_id
        )
    )
    preferred_channel_stmt = (
        select(Conversation.channel_id, func.count().label("message_count"))
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.customer_id == customer_id)
        .group_by(Conversation.channel_id)
        .order_by(func.count().desc())
        .limit(1)
    )
    preferred_channel_id = await session.scalar(preferred_channel_stmt)

    inbound_count = await session.scalar(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.customer_id == customer_id, Message.direction == "inbound")
    )
    outbound_count = await session.scalar(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.customer_id == customer_id, Message.direction == "outbound")
    )

    response_seconds_stmt = select(
        func.avg(
            func.extract("epoch", Conversation.first_response_at - Conversation.last_inbound_at)
        )
    ).where(
        Conversation.customer_id == customer_id,
        Conversation.first_response_at.isnot(None),
        Conversation.last_inbound_at.isnot(None),
    )
    average_response_seconds = await session.scalar(response_seconds_stmt)

    return CustomerCommunicationStatsOut(
        open_conversation_count=open_count or 0,
        total_inbound_messages=inbound_count or 0,
        total_outbound_messages=outbound_count or 0,
        last_contact_at=last_contact_at,
        preferred_channel_id=preferred_channel_id,
        average_response_seconds=float(average_response_seconds)
        if average_response_seconds is not None
        else None,
        unresolved_conversation_count=unresolved_count or 0,
    )


async def get_lead_communication_summary(
    session: AsyncSession, lead_id: uuid.UUID
) -> dict[str, Any]:
    last_contact_at = await session.scalar(
        select(func.max(Conversation.last_activity_at)).where(Conversation.lead_id == lead_id)
    )
    open_count = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.lead_id == lead_id,
            Conversation.status.not_in(("resolved", "closed", "spam")),
        )
    )
    assigned_staff_id = await session.scalar(
        select(Conversation.assigned_staff_id)
        .where(Conversation.lead_id == lead_id)
        .order_by(Conversation.last_activity_at.desc())
        .limit(1)
    )
    return {
        "last_contact_at": last_contact_at,
        "open_conversation_count": open_count or 0,
        "assigned_staff_id": assigned_staff_id,
    }


async def get_response_rate(
    session: AsyncSession, *, since: datetime | None = None
) -> float | None:
    """Fraction of conversations with an inbound message that have since
    received a staff reply — used by the analytics dashboard's "customer
    response rate," defined here once so its calculation stays consistent
    (this phase's own instruction's Analytics Definitions section)."""
    since = since or (datetime.now(UTC) - timedelta(days=30))
    total = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.last_inbound_at.isnot(None), Conversation.last_inbound_at >= since)
    )
    if not total:
        return None
    responded = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(
            Conversation.last_inbound_at.isnot(None),
            Conversation.last_inbound_at >= since,
            Conversation.first_response_at.isnot(None),
        )
    )
    return (responded or 0) / total
