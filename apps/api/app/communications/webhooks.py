"""Inbound-message and delivery-status webhook processing — this phase's
own instruction sections 15/16's 12-step flow, condensed to what the
signature-validated router entry points actually need: dedupe (unique
`(provider, provider_event_id)` insert), normalize via the provider
adapter, and hand off to `app.communications.messaging`.
"""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.messaging import apply_provider_status_event, ingest_inbound_message
from app.communications.providers import ProviderAdapter
from app.db.models import CommunicationChannel, InboundWebhookEvent, Message, ProviderStatusEvent


class WebhookSignatureError(ValueError):
    pass


# `ProviderStatusEvent.normalized_status` (this phase's own instruction
# section 16 vocabulary: accepted/queued/sent/delivered/read/failed/
# rejected/undeliverable) is intentionally not the same vocabulary as
# `Message.delivery_status` — a provider's "accepted" means "queued for
# processing" in the CRM's own lifecycle, and "rejected"/"undeliverable"
# both collapse to the single `failed` terminal state
# `app.communications.states` already defines.
_PROVIDER_STATUS_TO_MESSAGE_STATUS = {
    "accepted": "queued",
    "queued": "queued",
    "sent": "sent",
    "delivered": "delivered",
    "read": "read",
    "failed": "failed",
    "rejected": "failed",
    "undeliverable": "failed",
}


async def process_inbound_webhook(
    session: AsyncSession,
    *,
    provider: ProviderAdapter,
    channel: CommunicationChannel,
    headers: dict[str, str],
    raw_body: bytes,
    payload: dict[str, Any],
) -> InboundWebhookEvent:
    if not provider.validate_webhook_signature(headers=headers, raw_body=raw_body):
        raise WebhookSignatureError("Webhook signature validation failed.")

    normalized = provider.parse_inbound_webhook(payload)
    payload_hash = hashlib.sha256(raw_body).hexdigest()

    insert_stmt = (
        pg_insert(InboundWebhookEvent)
        .values(
            id=uuid.uuid4(),
            provider=provider.name,
            channel_id=channel.id,
            provider_event_id=normalized.provider_event_id,
            payload_hash=payload_hash,
            raw_payload=payload,
            processing_status="received",
        )
        .on_conflict_do_nothing(index_elements=["provider", "provider_event_id"])
        .returning(InboundWebhookEvent.id)
    )
    result = await session.execute(insert_stmt)
    inserted_id = result.scalar_one_or_none()
    if inserted_id is None:
        # Already processed once — a provider's at-least-once retry is a
        # no-op past the first insert (CLAUDE.md section 7).
        existing = await session.scalar(
            select(InboundWebhookEvent).where(
                InboundWebhookEvent.provider == provider.name,
                InboundWebhookEvent.provider_event_id == normalized.provider_event_id,
            )
        )
        assert existing is not None
        return existing

    event = await session.get(InboundWebhookEvent, inserted_id)
    assert event is not None

    message = await ingest_inbound_message(
        session,
        channel=channel,
        sender_reference=normalized.sender_reference,
        recipient_reference=normalized.recipient_reference,
        body_text=normalized.body_text,
        provider_message_id=normalized.provider_message_id,
        received_at=normalized.received_at,
    )
    event.processing_status = "processed"
    event.processed_at = datetime.now(UTC)
    event.resulting_message_id = message.id
    await session.flush()
    return event


async def process_status_webhook(
    session: AsyncSession,
    *,
    provider: ProviderAdapter,
    channel: CommunicationChannel,
    headers: dict[str, str],
    raw_body: bytes,
    payload: dict[str, Any],
) -> ProviderStatusEvent:
    if not provider.validate_webhook_signature(headers=headers, raw_body=raw_body):
        raise WebhookSignatureError("Webhook signature validation failed.")

    normalized = provider.parse_status_webhook(payload)

    insert_stmt = (
        pg_insert(ProviderStatusEvent)
        .values(
            id=uuid.uuid4(),
            provider=provider.name,
            channel_id=channel.id,
            provider_event_id=normalized.provider_event_id,
            normalized_status=normalized.normalized_status,
            raw_payload=payload,
            processing_status="received",
        )
        .on_conflict_do_nothing(index_elements=["provider", "provider_event_id"])
        .returning(ProviderStatusEvent.id)
    )
    result = await session.execute(insert_stmt)
    inserted_id = result.scalar_one_or_none()
    if inserted_id is None:
        existing = await session.scalar(
            select(ProviderStatusEvent).where(
                ProviderStatusEvent.provider == provider.name,
                ProviderStatusEvent.provider_event_id == normalized.provider_event_id,
            )
        )
        assert existing is not None
        return existing

    event = await session.get(ProviderStatusEvent, inserted_id)
    assert event is not None

    message = await session.scalar(
        select(Message).where(
            Message.channel_id == channel.id,
            Message.provider_message_id == normalized.provider_message_id,
        )
    )
    if message is None:
        event.processing_status = "ignored"
        event.error_message = "No matching message for provider_message_id."
        event.processed_at = datetime.now(UTC)
        await session.flush()
        return event

    event.message_id = message.id
    target_message_status = _PROVIDER_STATUS_TO_MESSAGE_STATUS.get(normalized.normalized_status)
    applied = False
    if target_message_status is not None:
        applied = await apply_provider_status_event(
            session,
            message=message,
            normalized_status=target_message_status,
            failure_code=normalized.failure_code,
            failure_reason=normalized.failure_reason,
        )
    event.processing_status = "processed" if applied else "ignored"
    event.processed_at = datetime.now(UTC)
    await session.flush()
    return event
