"""Scheduled-message processing engine — CLAUDE.md section 14 ("engine, not
scheduler"): no APScheduler/Celery-beat/cron framework is introduced here.
`process_due_scheduled_messages` is the explicit entry point a future
`apps/worker` job (or, until then, a manual/cron-invoked script) calls; it
is itself just a bounded, lockable batch query against `scheduled_messages`.

Also home to the retry classification used after a failed send attempt —
`app.communications.messaging.send_message` already records one attempt;
`retry_failed_message` is what re-queues a message whose last attempt was
retryable.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.messaging import send_message
from app.communications.service import (
    generate_conversation_number,
    get_conversation,
    record_message_status_transition,
)
from app.db.models import (
    CommunicationChannel,
    Conversation,
    Message,
    MessageDeliveryAttempt,
    MessageTemplate,
    ScheduledMessage,
)

_MAX_ATTEMPTS = 5


async def create_scheduled_conversation_for(
    session: AsyncSession, *, scheduled: ScheduledMessage, channel: CommunicationChannel
) -> Conversation:
    conversation = Conversation(
        conversation_number=generate_conversation_number(),
        channel_id=channel.id,
        customer_id=scheduled.customer_id,
        lead_id=scheduled.lead_id,
        status="open",
        priority="normal",
        source="system_event",
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def process_due_scheduled_messages(
    session: AsyncSession, *, now: datetime | None = None, batch_size: int = 50
) -> list[uuid.UUID]:
    """Locks a bounded batch of due rows (`processing_locked_at`) so two
    concurrent invocations of this entry point cannot double-send the same
    scheduled message — the same idempotency concern this phase's own
    instruction section 21 names."""
    now = now or datetime.now(UTC)
    due = (
        await session.scalars(
            select(ScheduledMessage)
            .where(
                ScheduledMessage.status == "scheduled",
                ScheduledMessage.scheduled_for <= now,
                ScheduledMessage.processing_locked_at.is_(None),
            )
            .order_by(ScheduledMessage.scheduled_for)
            .limit(batch_size)
        )
    ).all()

    processed_ids: list[uuid.UUID] = []
    for scheduled in due:
        scheduled.processing_locked_at = now
        scheduled.status = "processing"
        await session.flush()

        channel = await session.get(CommunicationChannel, scheduled.channel_id)
        template = (
            await session.get(MessageTemplate, scheduled.template_id)
            if scheduled.template_id
            else None
        )
        conversation: Conversation | None = None
        if scheduled.conversation_id is not None:
            conversation = await get_conversation(session, scheduled.conversation_id)
        if conversation is None:
            assert channel is not None
            conversation = await create_scheduled_conversation_for(
                session, scheduled=scheduled, channel=channel
            )

        scheduled.attempt_count += 1
        try:
            assert channel is not None
            message = await send_message(
                session,
                conversation=conversation,
                channel=channel,
                recipient_reference=scheduled.recipient_reference,
                body_text=None,
                message_type="template" if template else "text",
                template=template,
                template_variables=scheduled.template_variables,
                idempotency_key=f"scheduled:{scheduled.id}:{scheduled.attempt_count}",
            )
            scheduled.status = "sent"
            scheduled.result_message_id = message.id
        except Exception as exc:  # a rendering/eligibility failure keeps the batch moving
            scheduled.status = "failed" if scheduled.attempt_count >= _MAX_ATTEMPTS else "scheduled"
            scheduled.last_error = str(exc)
        finally:
            scheduled.processing_locked_at = None
        processed_ids.append(scheduled.id)

    await session.flush()
    return processed_ids


async def cancel_scheduled_message(
    session: AsyncSession, *, scheduled: ScheduledMessage, actor_id: uuid.UUID
) -> ScheduledMessage:
    scheduled.status = "cancelled"
    scheduled.cancelled_at = datetime.now(UTC)
    scheduled.cancelled_by = actor_id
    await session.flush()
    return scheduled


async def retry_failed_message(session: AsyncSession, *, message: Message) -> Message | None:
    """Re-queues a `failed` outbound message whose most recent delivery
    attempt was marked retryable — a permanent failure has no retry path
    (CLAUDE.md section 20: "Do not retry permanent failures")."""
    last_attempt = await session.scalar(
        select(MessageDeliveryAttempt)
        .where(MessageDeliveryAttempt.message_id == message.id)
        .order_by(MessageDeliveryAttempt.attempt_number.desc())
        .limit(1)
    )
    if last_attempt is None or not last_attempt.is_retryable:
        return None
    if message.retry_count >= _MAX_ATTEMPTS:
        return None
    message.retry_count += 1
    record_message_status_transition(
        session, message=message, target_status="queued", source="system", actor_id=None
    )
    await session.flush()
    return message


async def retry_all_failed_messages(session: AsyncSession, *, batch_size: int = 50) -> int:
    """The Phase 15 scheduler's entry point — `retry_failed_message` only
    knows how to retry *one* message and has no "find failed retryable
    messages" selector of its own; it already safely no-ops (returns
    `None`) for a message whose last attempt was permanent or that has
    exhausted `_MAX_ATTEMPTS`, so this simply calls it once per candidate
    and lets that existing guard decide."""
    candidates = (
        await session.scalars(
            select(Message)
            .where(
                Message.direction == "outbound",
                Message.delivery_status == "failed",
                Message.retry_count < _MAX_ATTEMPTS,
            )
            .order_by(Message.created_at)
            .limit(batch_size)
        )
    ).all()
    retried = 0
    for message in candidates:
        result = await retry_failed_message(session, message=message)
        if result is not None:
            retried += 1
    return retried
