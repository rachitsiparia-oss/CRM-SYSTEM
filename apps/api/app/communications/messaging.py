"""Outbound send and inbound ingestion orchestration — the layer that ties
together templates, consent/suppression, the provider adapter, and the
message state machine. `app.communications.webhooks` calls
`ingest_inbound_message` after normalizing a provider payload;
`app.communications.router` and `app.communications.integrations` call
`send_message` for staff replies and domain-triggered notifications alike.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.consent import evaluate_send_eligibility
from app.communications.providers import get_provider
from app.communications.service import (
    generate_conversation_number,
    record_message_status_transition,
)
from app.communications.states import is_message_transition_allowed
from app.communications.templates import render_template
from app.db.models import (
    CommunicationChannel,
    Conversation,
    ConversationStatusHistory,
    Customer,
    Lead,
    Message,
    MessageDeliveryAttempt,
    MessageStatusHistory,
    MessageTemplate,
    StaffUser,
)
from app.outbox.service import record_domain_event


class MessageSendError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


async def send_message(
    session: AsyncSession,
    *,
    conversation: Conversation,
    channel: CommunicationChannel,
    recipient_reference: str | None,
    body_text: str | None,
    message_type: str = "text",
    template: MessageTemplate | None = None,
    template_variables: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    actor: StaffUser | None = None,
    is_transactional: bool = True,
) -> Message:
    rendered_body = body_text
    rendered_subject: str | None = None
    if template is not None:
        rendered_body, rendered_subject = render_template(
            body=template.body,
            subject=template.subject,
            declared_variables=template.variables,
            values=template_variables or {},
        )
        is_transactional = template.is_transactional

    eligibility = await evaluate_send_eligibility(
        session,
        channel=channel,
        destination_reference=recipient_reference,
        customer_id=conversation.customer_id,
        is_transactional=is_transactional,
    )

    now = datetime.now(UTC)
    message = Message(
        conversation_id=conversation.id,
        channel_id=channel.id,
        direction="outbound",
        message_type=message_type,
        recipient_reference=recipient_reference,
        subject=rendered_subject,
        body_text=rendered_body,
        template_id=template.id if template else None,
        rendered_template_variables=template_variables,
        idempotency_key=idempotency_key,
        delivery_status="draft",
        created_by=actor.id if actor else None,
    )
    session.add(message)
    await session.flush()
    session.add(
        MessageStatusHistory(
            message_id=message.id, previous_status=None, new_status="draft", source="system"
        )
    )

    if not eligibility.allowed:
        record_message_status_transition(
            session,
            message=message,
            target_status="queued",
            source="system",
            actor_id=actor.id if actor else None,
        )
        record_message_status_transition(
            session,
            message=message,
            target_status="suppressed",
            source="system",
            actor_id=None,
            reason=eligibility.reason,
        )
        await session.flush()
        return message

    record_message_status_transition(
        session,
        message=message,
        target_status="queued",
        source="system",
        actor_id=actor.id if actor else None,
    )
    record_message_status_transition(
        session, message=message, target_status="processing", source="system", actor_id=None
    )
    await session.flush()

    provider = get_provider(channel.provider)
    attempt_started = datetime.now(UTC)
    try:
        if template is not None:
            result = await provider.send_template(
                recipient_reference=recipient_reference or "",
                template_code=template.code,
                rendered_body=rendered_body or "",
            )
        else:
            result = await provider.send_text(
                recipient_reference=recipient_reference or "", body=rendered_body or ""
            )
    except (
        Exception
    ) as exc:  # provider transport failure — recorded, never re-raised past this boundary
        session.add(
            MessageDeliveryAttempt(
                message_id=message.id,
                attempt_number=1,
                provider=provider.name,
                started_at=attempt_started,
                finished_at=datetime.now(UTC),
                result="network_timeout",
                is_retryable=True,
            )
        )
        record_message_status_transition(
            session,
            message=message,
            target_status="failed",
            source="system",
            actor_id=None,
            reason=str(exc),
        )
        message.failure_code = "network_timeout"
        message.failure_reason = str(exc)
        message.failed_at = datetime.now(UTC)
        await session.flush()
        return message

    session.add(
        MessageDeliveryAttempt(
            message_id=message.id,
            attempt_number=1,
            provider=provider.name,
            started_at=attempt_started,
            finished_at=datetime.now(UTC),
            result="success" if result.accepted else "permanent_failure",
            provider_response_code=result.failure_code,
        )
    )
    if result.accepted:
        message.provider_message_id = result.provider_message_id
        record_message_status_transition(
            session, message=message, target_status="sent", source="system", actor_id=None
        )
        message.sent_at = now
        conversation.last_outbound_at = now
        conversation.last_activity_at = now
        if conversation.first_response_at is None and conversation.status in (
            "open",
            "pending",
            "waiting_on_staff",
        ):
            conversation.first_response_at = now
        await record_domain_event(
            session,
            event_type="communication.message.sent",
            aggregate_type="message",
            aggregate_id=message.id,
            payload={"conversation_id": str(conversation.id)},
        )
    else:
        record_message_status_transition(
            session,
            message=message,
            target_status="failed",
            source="system",
            actor_id=None,
            reason=result.failure_reason,
        )
        message.failure_code = result.failure_code
        message.failure_reason = result.failure_reason
        message.failed_at = now
    await session.flush()
    return message


async def _find_or_create_conversation_for_inbound(
    session: AsyncSession,
    *,
    channel: CommunicationChannel,
    sender_reference: str,
) -> Conversation:
    customer = await session.scalar(
        select(Customer).where(Customer.primary_phone_e164 == sender_reference)
    )
    if customer is None:
        customer = await session.scalar(
            select(Customer).where(Customer.primary_email == sender_reference)
        )
    lead: Lead | None = None
    if customer is None:
        lead = await session.scalar(select(Lead).where(Lead.phone_e164 == sender_reference))

    query = select(Conversation).where(
        Conversation.channel_id == channel.id,
        Conversation.status.not_in(("closed", "resolved", "spam")),
    )
    if customer is not None:
        query = query.where(Conversation.customer_id == customer.id)
    elif lead is not None:
        query = query.where(Conversation.lead_id == lead.id)
    else:
        query = query.where(Conversation.phone_e164 == sender_reference)

    conversation = await session.scalar(query.order_by(Conversation.last_activity_at.desc()))
    if conversation is not None:
        return conversation

    conversation = Conversation(
        conversation_number=generate_conversation_number(),
        channel_id=channel.id,
        customer_id=customer.id if customer else None,
        lead_id=lead.id if lead else None,
        phone_e164=sender_reference if channel.code in ("sms", "whatsapp") else None,
        email=sender_reference if channel.code == "email" else None,
        status="open",
        priority="normal",
        source="inbound",
        unread_count=0,
    )
    session.add(conversation)
    await session.flush()
    session.add(
        ConversationStatusHistory(
            conversation_id=conversation.id, previous_status=None, new_status="open", actor_id=None
        )
    )
    await record_domain_event(
        session,
        event_type="communication.conversation.created",
        aggregate_type="conversation",
        aggregate_id=conversation.id,
        payload={"source": "inbound"},
    )
    return conversation


async def ingest_inbound_message(
    session: AsyncSession,
    *,
    channel: CommunicationChannel,
    sender_reference: str,
    recipient_reference: str | None,
    body_text: str | None,
    provider_message_id: str | None,
    received_at: datetime,
) -> Message:
    conversation = await _find_or_create_conversation_for_inbound(
        session, channel=channel, sender_reference=sender_reference
    )
    conversation.last_inbound_at = received_at
    conversation.last_activity_at = received_at
    conversation.unread_count += 1
    if conversation.status in ("resolved", "closed", "waiting_on_customer"):
        conversation.status = "open"
        session.add(
            ConversationStatusHistory(
                conversation_id=conversation.id,
                previous_status="waiting_on_customer",
                new_status="open",
                actor_id=None,
                reason="Inbound message received.",
            )
        )
    elif conversation.status == "waiting_on_staff":
        pass
    else:
        conversation.status = (
            "waiting_on_staff" if conversation.status == "open" else conversation.status
        )

    message = Message(
        conversation_id=conversation.id,
        channel_id=channel.id,
        direction="inbound",
        message_type=channel.code if channel.code in ("email", "sms", "whatsapp") else "text",
        sender_reference=sender_reference,
        recipient_reference=recipient_reference,
        body_text=body_text,
        provider_message_id=provider_message_id,
        delivery_status="received",
        received_at=received_at,
    )
    session.add(message)
    await session.flush()
    session.add(
        MessageStatusHistory(
            message_id=message.id, previous_status=None, new_status="received", source="webhook"
        )
    )
    await record_domain_event(
        session,
        event_type="communication.inbound.received",
        aggregate_type="message",
        aggregate_id=message.id,
        payload={"conversation_id": str(conversation.id)},
    )
    await session.flush()
    return message


async def apply_provider_status_event(
    session: AsyncSession,
    *,
    message: Message,
    normalized_status: str,
    failure_code: str | None = None,
    failure_reason: str | None = None,
) -> bool:
    """Applies a normalized delivery-status webhook to a message. Returns
    False (no-op) for an out-of-order or already-applied event — the
    caller (`app.communications.webhooks`) still marks the raw webhook
    event as processed either way, since "ignored because out of order" is
    a successful, idempotent outcome, not a failure."""
    if not is_message_transition_allowed(
        message.direction, message.delivery_status, normalized_status
    ):
        return False
    applied = record_message_status_transition(
        session, message=message, target_status=normalized_status, source="webhook", actor_id=None
    )
    if not applied:
        return False
    now = datetime.now(UTC)
    if normalized_status == "delivered":
        message.delivered_at = now
    elif normalized_status == "read":
        message.read_at = now
    elif normalized_status == "failed":
        message.failed_at = now
        message.failure_code = failure_code
        message.failure_reason = failure_reason
    await session.flush()
    return True
