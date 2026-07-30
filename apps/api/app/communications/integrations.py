"""Reservation and order communication integration — consumes the existing
Phase 9/Phase 7 outbox events (`reservation.created`, `reservation.status_
changed`, `order.created`, `order.status_changed`) to drive Communication
Hub conversations/messages and operational notifications, without touching
either domain's own state machine (this phase's own instruction: "Do not
alter reservation availability/assignment/state-transition logic except
where a narrow integration hook is required").

`process_pending_communication_events` is the explicit engine entry point
(CLAUDE.md section 14, "engine, not scheduler") — nothing calls it on a
timer yet; recurring/automatic dispatch through `apps/worker` is Phase 15's
own scope (ARQ jobs/scheduler), the same "provides the deterministic
mechanism, not the automatic trigger" split Phase 9 left for reminder
dispatch. A failed communication attempt never rolls back or corrupts the
reservation/order it describes — this function only ever reads Reservation/
Order state and writes Communication Hub + Notification rows.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.messaging import send_message
from app.communications.service import generate_conversation_number
from app.db.models import (
    CommunicationChannel,
    Conversation,
    ConversationLink,
    Customer,
    MessageTemplate,
    Order,
    OutboxEvent,
    Reservation,
)
from app.notifications.service import notify

_RESERVATION_STATUS_TEMPLATE_CATEGORY = {
    "confirmed": "reservation_confirmation",
    "cancelled_by_customer": "reservation_cancellation",
    "cancelled_by_restaurant": "reservation_cancellation",
}
_ORDER_STATUS_TEMPLATE_CATEGORY = {
    "confirmed": "order_confirmation",
    "ready": "order_ready",
    "cancelled": "order_cancellation",
}

_CONSUMED_EVENT_TYPES = (
    "reservation.created",
    "reservation.status_changed",
    "order.created",
    "order.status_changed",
)


async def _get_or_create_linked_conversation(
    session: AsyncSession,
    *,
    channel: CommunicationChannel,
    customer_id: uuid.UUID | None,
    linked_type: str,
    linked_id: uuid.UUID,
) -> Conversation:
    existing_link = await session.scalar(
        select(ConversationLink).where(
            ConversationLink.linked_type == linked_type,
            ConversationLink.linked_id == linked_id,
            ConversationLink.unlinked_at.is_(None),
        )
    )
    if existing_link is not None:
        conversation = await session.get(Conversation, existing_link.conversation_id)
        if conversation is not None:
            return conversation

    conversation = Conversation(
        conversation_number=generate_conversation_number(),
        channel_id=channel.id,
        customer_id=customer_id,
        status="open",
        priority="normal",
        source="system_event",
    )
    session.add(conversation)
    await session.flush()
    session.add(
        ConversationLink(
            conversation_id=conversation.id, linked_type=linked_type, linked_id=linked_id
        )
    )
    await session.flush()
    return conversation


async def _find_active_template(
    session: AsyncSession, *, channel_id: uuid.UUID, category: str
) -> MessageTemplate | None:
    template: MessageTemplate | None = await session.scalar(
        select(MessageTemplate)
        .where(
            MessageTemplate.channel_id == channel_id,
            MessageTemplate.category == category,
            MessageTemplate.status == "active",
        )
        .limit(1)
    )
    return template


async def _default_channel(session: AsyncSession, *, code: str) -> CommunicationChannel | None:
    channel: CommunicationChannel | None = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.code == code)
    )
    return channel


async def handle_reservation_event(session: AsyncSession, *, event: OutboxEvent) -> bool:
    reservation = await session.get(Reservation, event.aggregate_id)
    if reservation is None:
        return False

    if event.event_type == "reservation.created":
        # CLAUDE.md section 23: "Every new reservation should create an
        # operational notification." A new request is rarely assigned yet,
        # so the recipient is whoever created it (always a real staff
        # member — walk-ins and phone/online requests are all entered by
        # staff) rather than a not-yet-assigned staff member.
        recipient_id = reservation.assigned_staff_id or reservation.created_by
        if recipient_id is not None:
            await notify(
                session,
                notification_type="reservation.created",
                title=f"New reservation {reservation.reservation_number}",
                body=f"{reservation.guest_name} — party of {reservation.party_size}.",
                record_type="reservation",
                record_id=reservation.id,
                recipient_staff_id=recipient_id,
                dedup_key=f"reservation.created:{reservation.id}",
            )
        return True

    new_status = event.payload.get("new_status")
    category = _RESERVATION_STATUS_TEMPLATE_CATEGORY.get(new_status) if new_status else None
    if category is None:
        return True  # not every status transition has an outbound message

    channel = await _default_channel(session, code="whatsapp")
    if channel is None or not reservation.phone_e164:
        return True

    template = await _find_active_template(session, channel_id=channel.id, category=category)
    conversation = await _get_or_create_linked_conversation(
        session,
        channel=channel,
        customer_id=reservation.customer_id,
        linked_type="reservation",
        linked_id=reservation.id,
    )
    variables = {
        "customer_name": reservation.guest_name,
        "reservation_number": reservation.reservation_number,
        "reservation_date": reservation.reservation_date.isoformat(),
        "reservation_time": reservation.start_time.isoformat(),
        "party_size": str(reservation.party_size),
    }
    if template is not None:
        declared = set(template.variables)
        variables = {k: v for k, v in variables.items() if k in declared}
    await send_message(
        session,
        conversation=conversation,
        channel=channel,
        recipient_reference=reservation.phone_e164,
        body_text=None
        if template
        else f"Your reservation {reservation.reservation_number} is now {new_status}.",
        message_type="reservation_update",
        template=template,
        template_variables=variables if template else None,
        idempotency_key=f"reservation.status_changed:{reservation.id}:{new_status}",
    )
    return True


async def handle_order_event(session: AsyncSession, *, event: OutboxEvent) -> bool:
    order = await session.get(Order, event.aggregate_id)
    if order is None:
        return False

    if event.event_type == "order.created":
        recipient_id = order.assigned_staff_id or order.created_by
        if recipient_id is not None:
            await notify(
                session,
                notification_type="order.created",
                title=f"New order {order.order_number}",
                body=f"Order {order.order_number} placed.",
                record_type="order",
                record_id=order.id,
                recipient_staff_id=recipient_id,
                dedup_key=f"order.created:{order.id}",
            )
        return True

    if order.customer_id is None:
        return True  # no linked customer contact to message

    new_status = event.payload.get("new_status")
    category = _ORDER_STATUS_TEMPLATE_CATEGORY.get(new_status) if new_status else None
    if category is None:
        return True

    customer = await session.get(Customer, order.customer_id)
    if customer is None or not customer.primary_phone_e164:
        return True

    channel = await _default_channel(session, code="whatsapp")
    if channel is None:
        return True

    template = await _find_active_template(session, channel_id=channel.id, category=category)
    conversation = await _get_or_create_linked_conversation(
        session,
        channel=channel,
        customer_id=order.customer_id,
        linked_type="order",
        linked_id=order.id,
    )
    variables = {"order_number": order.order_number, "order_status": new_status}
    if template is not None:
        declared = set(template.variables)
        variables = {k: v for k, v in variables.items() if k in declared}
    await send_message(
        session,
        conversation=conversation,
        channel=channel,
        recipient_reference=customer.primary_phone_e164,
        body_text=None if template else f"Your order {order.order_number} is now {new_status}.",
        message_type="order_update",
        template=template,
        template_variables=variables if template else None,
        idempotency_key=f"order.status_changed:{order.id}:{new_status}",
    )
    return True


async def process_pending_communication_events(
    session: AsyncSession, *, batch_size: int = 50
) -> dict[str, int]:
    events = (
        await session.scalars(
            select(OutboxEvent)
            .where(
                OutboxEvent.status == "pending", OutboxEvent.event_type.in_(_CONSUMED_EVENT_TYPES)
            )
            .order_by(OutboxEvent.available_at)
            .limit(batch_size)
        )
    ).all()

    results = {"published": 0, "failed": 0}
    for event in events:
        event.status = "processing"
        event.attempts += 1
        try:
            if event.aggregate_type == "reservation":
                handled = await handle_reservation_event(session, event=event)
            elif event.aggregate_type == "order":
                handled = await handle_order_event(session, event=event)
            else:
                handled = True
            event.status = "published" if handled else "failed_retryable"
            if handled:
                event.completed_at = datetime.now(UTC)
                results["published"] += 1
            else:
                results["failed"] += 1
        except Exception as exc:  # a communication failure never corrupts the source record
            event.status = "failed_retryable"
            event.last_error = str(exc)
            results["failed"] += 1
        await session.flush()
    return results
