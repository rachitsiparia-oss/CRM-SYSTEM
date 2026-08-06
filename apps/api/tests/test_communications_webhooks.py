import uuid

import pytest
from app.communications.providers import InternalMockProvider, get_registered_provider
from app.communications.webhooks import process_inbound_webhook, process_status_webhook
from app.db.models import CommunicationChannel, InboundWebhookEvent, Message
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def _whatsapp_channel(session: AsyncSession) -> CommunicationChannel:
    channel = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.code == "whatsapp")
    )
    assert channel is not None
    return channel


async def test_inbound_webhook_is_deduplicated(db_session: AsyncSession) -> None:
    channel = await _whatsapp_channel(db_session)
    provider = InternalMockProvider()
    event_id = f"evt-{uuid.uuid4().hex}"
    payload = {"event_id": event_id, "from": "+919800011122", "body": "Hi there"}

    first = await process_inbound_webhook(
        db_session, provider=provider, channel=channel, headers={}, raw_body=b"{}", payload=payload
    )
    second = await process_inbound_webhook(
        db_session, provider=provider, channel=channel, headers={}, raw_body=b"{}", payload=payload
    )

    assert first.id == second.id  # the second call resolved the same ledger row
    ledger_count = await db_session.scalar(
        select(InboundWebhookEvent.id).where(InboundWebhookEvent.provider_event_id == event_id)
    )
    assert ledger_count is not None
    message_count = await db_session.scalar(
        select(Message.id).where(Message.sender_reference == "+919800011122")
    )
    assert message_count is not None
    # Exactly one message was created despite two identical webhook deliveries.
    all_matching = (
        await db_session.scalars(select(Message).where(Message.sender_reference == "+919800011122"))
    ).all()
    assert len(all_matching) == 1


async def test_status_webhook_is_deduplicated_and_progresses_forward(
    db_session: AsyncSession,
) -> None:
    channel = await _whatsapp_channel(db_session)
    provider = InternalMockProvider()

    inbound_result = await process_inbound_webhook(
        db_session,
        provider=provider,
        channel=channel,
        headers={},
        raw_body=b"{}",
        payload={"event_id": f"evt-{uuid.uuid4().hex}", "from": "+919800022233", "body": "Order?"},
    )
    assert inbound_result.resulting_message_id is not None
    inbound_message = await db_session.get(Message, inbound_result.resulting_message_id)
    assert inbound_message is not None

    # Manufacture an outbound message the status webhook can target.
    outbound = Message(
        conversation_id=inbound_message.conversation_id,
        channel_id=channel.id,
        direction="outbound",
        message_type="whatsapp",
        recipient_reference="+919800022233",
        provider_message_id="prov-msg-123",
        delivery_status="sent",
    )
    db_session.add(outbound)
    await db_session.flush()

    status_event_id = f"status-{uuid.uuid4().hex}"
    payload = {
        "event_id": status_event_id,
        "provider_message_id": "prov-msg-123",
        "status": "delivered",
    }

    first = await process_status_webhook(
        db_session, provider=provider, channel=channel, headers={}, raw_body=b"{}", payload=payload
    )
    second = await process_status_webhook(
        db_session, provider=provider, channel=channel, headers={}, raw_body=b"{}", payload=payload
    )
    assert first.id == second.id

    await db_session.refresh(outbound)
    assert outbound.delivery_status == "delivered"

    # An out-of-order "sent" arriving after "delivered" must not regress it.
    stale_event_id = f"status-{uuid.uuid4().hex}"
    stale_payload = {
        "event_id": stale_event_id,
        "provider_message_id": "prov-msg-123",
        "status": "sent",
    }
    stale_result = await process_status_webhook(
        db_session,
        provider=provider,
        channel=channel,
        headers={},
        raw_body=b"{}",
        payload=stale_payload,
    )
    assert stale_result.processing_status == "ignored"
    await db_session.refresh(outbound)
    assert outbound.delivery_status == "delivered"


async def test_status_webhook_ignored_when_no_matching_message(db_session: AsyncSession) -> None:
    channel = await _whatsapp_channel(db_session)
    provider = InternalMockProvider()
    payload = {
        "event_id": f"status-{uuid.uuid4().hex}",
        "provider_message_id": "no-such-message",
        "status": "delivered",
    }
    result = await process_status_webhook(
        db_session, provider=provider, channel=channel, headers={}, raw_body=b"{}", payload=payload
    )
    assert result.processing_status == "ignored"
    assert result.message_id is None


async def test_get_registered_provider_has_no_mock_fallback() -> None:
    # Unlike get_provider(), an unregistered name must resolve to None, not
    # silently degrade to InternalMockProvider — see providers.py's
    # docstring for why that fallback would be unsafe on the webhook path.
    assert get_registered_provider("not_a_real_adapter") is None
    assert get_registered_provider("internal_mock") is not None


async def test_inbound_webhook_rejects_channel_with_unregistered_provider(
    authed_client: AsyncClient, db_session: AsyncSession
) -> None:
    # `code` is restricted to CHANNEL_CODES by a check constraint, so this
    # reuses the already-seeded "whatsapp" channel rather than inserting a
    # new row — only `provider` (free text, no allowlist) is repointed at a
    # name with no registered adapter, which is exactly the scenario the
    # fix guards against. The SAVEPOINT-scoped db_session rolls this back.
    channel = await _whatsapp_channel(db_session)
    channel.provider = "not_a_real_adapter"
    await db_session.flush()

    response = await authed_client.post(
        "/api/v1/communications/webhooks/not_a_real_adapter/inbound",
        json={"event_id": "evt-1", "from": "+919800099999", "body": "hi"},
    )
    assert response.status_code == 503
