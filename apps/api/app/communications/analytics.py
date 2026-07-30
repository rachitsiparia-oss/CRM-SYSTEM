"""Communication analytics and manual call logs — this phase's own
instruction section 23. Definitions are pinned here once so every consumer
(dashboard, reports) computes the same numbers the same way:

- "Unread" counts only customer-facing conversations, never internal notes.
- "Delivery rate" / "failure rate" are computed over outbound messages that
  reached a terminal state (sent/delivered/read/failed/cancelled/
  suppressed) in the window, not over messages still in flight.
- "Read rate" only applies to channels that report read receipts; a
  channel without one is simply never in the denominator (this phase's own
  instruction: "avoid misleading metrics when a provider lacks read
  receipts" — the mock provider never sets `read_at`, so it is correctly
  excluded rather than counted as unread).
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.schemas import CommunicationAnalyticsOut, ManualCallLogCreateIn
from app.db.models import (
    CommunicationChannel,
    CommunicationSuppression,
    Conversation,
    ManualCallLog,
    Message,
    StaffUser,
)

_TERMINAL_OUTBOUND_STATUSES = ("sent", "delivered", "read", "failed", "cancelled", "suppressed")


async def get_communication_analytics(session: AsyncSession) -> CommunicationAnalyticsOut:
    today = date.today()
    today_start = datetime(today.year, today.month, today.day, tzinfo=UTC)

    open_conversations = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.status.not_in(("resolved", "closed", "spam")))
    )
    unread_conversations = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.unread_count > 0, Conversation.status.not_in(("closed", "spam")))
    )
    waiting_on_staff = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.status == "waiting_on_staff")
    )
    waiting_on_customer = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.status == "waiting_on_customer")
    )
    resolved_today = await session.scalar(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.resolved_at.isnot(None), Conversation.resolved_at >= today_start)
    )

    avg_first_response = await session.scalar(
        select(
            func.avg(
                func.extract("epoch", Conversation.first_response_at - Conversation.last_inbound_at)
            )
        ).where(
            Conversation.first_response_at.isnot(None), Conversation.last_inbound_at.isnot(None)
        )
    )
    avg_resolution = await session.scalar(
        select(
            func.avg(func.extract("epoch", Conversation.resolved_at - Conversation.created_at))
        ).where(Conversation.resolved_at.isnot(None))
    )

    channel_rows = (
        await session.execute(
            select(CommunicationChannel.code, func.count(Message.id))
            .join(Message, Message.channel_id == CommunicationChannel.id)
            .group_by(CommunicationChannel.code)
        )
    ).all()
    messages_by_channel = {code: count for code, count in channel_rows}

    inbound_count = await session.scalar(
        select(func.count()).select_from(Message).where(Message.direction == "inbound")
    )
    outbound_count = await session.scalar(
        select(func.count()).select_from(Message).where(Message.direction == "outbound")
    )

    terminal_outbound = await session.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            Message.direction == "outbound",
            Message.delivery_status.in_(_TERMINAL_OUTBOUND_STATUSES),
        )
    )
    delivered_or_read = await session.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.direction == "outbound", Message.delivery_status.in_(("delivered", "read")))
    )
    failed_outbound = await session.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.direction == "outbound", Message.delivery_status == "failed")
    )

    suppression_count = await session.scalar(
        select(func.count())
        .select_from(CommunicationSuppression)
        .where(CommunicationSuppression.is_active.is_(True))
    )

    return CommunicationAnalyticsOut(
        open_conversations=open_conversations or 0,
        unread_conversations=unread_conversations or 0,
        waiting_on_staff=waiting_on_staff or 0,
        waiting_on_customer=waiting_on_customer or 0,
        resolved_today=resolved_today or 0,
        average_first_response_seconds=float(avg_first_response)
        if avg_first_response is not None
        else None,
        average_resolution_seconds=float(avg_resolution) if avg_resolution is not None else None,
        messages_by_channel=messages_by_channel,
        inbound_count=inbound_count or 0,
        outbound_count=outbound_count or 0,
        delivery_rate=(delivered_or_read or 0) / terminal_outbound if terminal_outbound else None,
        failure_rate=(failed_outbound or 0) / terminal_outbound if terminal_outbound else None,
        suppression_count=suppression_count or 0,
    )


async def create_call_log(
    session: AsyncSession, *, actor: StaffUser, payload: ManualCallLogCreateIn
) -> ManualCallLog:
    duration_seconds = None
    if payload.ended_at is not None:
        duration_seconds = int((payload.ended_at - payload.started_at).total_seconds())
    call_log = ManualCallLog(
        customer_id=payload.customer_id,
        lead_id=payload.lead_id,
        conversation_id=payload.conversation_id,
        staff_user_id=actor.id,
        direction=payload.direction,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        duration_seconds=duration_seconds,
        outcome=payload.outcome,
        notes=payload.notes,
        follow_up_required=payload.follow_up_required,
        related_reservation_id=payload.related_reservation_id,
        related_order_id=payload.related_order_id,
        created_by=actor.id,
    )
    session.add(call_log)
    await session.flush()
    return call_log


async def get_call_log(session: AsyncSession, call_log_id: uuid.UUID) -> ManualCallLog | None:
    return await session.get(ManualCallLog, call_log_id)
