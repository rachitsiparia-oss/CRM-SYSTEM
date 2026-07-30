import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models import (
    CommunicationChannel,
    Conversation,
    Message,
    TaskRecord,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def _get_whatsapp_channel_id(session: AsyncSession) -> uuid.UUID:
    channel_id = await session.scalar(
        select(CommunicationChannel.id).where(CommunicationChannel.code == "whatsapp")
    )
    assert channel_id is not None, "whatsapp channel was not seeded"
    return channel_id


def _conversation_kwargs(channel_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "conversation_number": f"CONV-{suffix}",
        "channel_id": channel_id,
        "status": "open",
        "priority": "normal",
        "source": "staff_initiated",
    }
    base.update(overrides)
    return base


async def _make_conversation(
    session: AsyncSession, channel_id: uuid.UUID, **overrides: object
) -> Conversation:
    conversation = Conversation(**_conversation_kwargs(channel_id, **overrides))
    session.add(conversation)
    await session.flush()
    return conversation


def _message_kwargs(
    conversation_id: uuid.UUID, channel_id: uuid.UUID, **overrides: object
) -> dict[str, object]:
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "conversation_id": conversation_id,
        "channel_id": channel_id,
        "direction": "outbound",
        "message_type": "text",
        "recipient_reference": "+919800000000",
        "delivery_status": "draft",
    }
    base.update(overrides)
    return base


# --- Conversation --------------------------------------------------------


async def test_conversation_rejects_invalid_status(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    db_session.add(Conversation(**_conversation_kwargs(channel_id, status="on_fire")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_conversation_rejects_invalid_priority(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    db_session.add(Conversation(**_conversation_kwargs(channel_id, priority="critical")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_conversation_rejects_negative_unread_count(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    db_session.add(Conversation(**_conversation_kwargs(channel_id, unread_count=-1)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- Message ---------------------------------------------------------------


async def test_message_rejects_invalid_direction(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    conversation = await _make_conversation(db_session, channel_id)
    db_session.add(Message(**_message_kwargs(conversation.id, channel_id, direction="sideways")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_message_outbound_requires_recipient(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    conversation = await _make_conversation(db_session, channel_id)
    db_session.add(
        Message(
            **_message_kwargs(
                conversation.id, channel_id, direction="outbound", recipient_reference=None
            )
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_internal_note_cannot_have_external_recipient(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    conversation = await _make_conversation(db_session, channel_id)
    db_session.add(
        Message(
            **_message_kwargs(
                conversation.id,
                channel_id,
                direction="internal",
                message_type="internal_note",
                delivery_status="created",
                recipient_reference="+919800000000",
            )
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_message_delivered_cannot_precede_sent(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    conversation = await _make_conversation(db_session, channel_id)
    now = datetime.now(UTC)
    db_session.add(
        Message(
            **_message_kwargs(
                conversation.id,
                channel_id,
                delivery_status="delivered",
                sent_at=now,
                delivered_at=now.replace(year=now.year - 1),
            )
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_message_read_cannot_precede_delivered(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    conversation = await _make_conversation(db_session, channel_id)
    now = datetime.now(UTC)
    db_session.add(
        Message(
            **_message_kwargs(
                conversation.id,
                channel_id,
                delivery_status="read",
                sent_at=now,
                delivered_at=now,
                read_at=now.replace(year=now.year - 1),
            )
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_message_valid_ordering_is_accepted(db_session: AsyncSession) -> None:
    channel_id = await _get_whatsapp_channel_id(db_session)
    conversation = await _make_conversation(db_session, channel_id)
    sent = datetime.now(UTC)
    delivered = sent + timedelta(seconds=1)
    db_session.add(
        Message(
            **_message_kwargs(
                conversation.id,
                channel_id,
                delivery_status="delivered",
                sent_at=sent,
                delivered_at=delivered,
            )
        )
    )
    await db_session.flush()  # should not raise


# --- TaskRecord --------------------------------------------------------


def _task_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "task_number": f"TASK-{suffix}",
        "title": "Test task",
        "source": "manual",
        "priority": "normal",
        "status": "open",
    }
    base.update(overrides)
    return base


async def test_task_rejects_invalid_status(db_session: AsyncSession) -> None:
    db_session.add(TaskRecord(**_task_kwargs(status="not_a_status")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_task_blocked_requires_reason(db_session: AsyncSession) -> None:
    db_session.add(TaskRecord(**_task_kwargs(status="blocked", blocked_reason=None)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_task_blocked_with_reason_is_accepted(db_session: AsyncSession) -> None:
    db_session.add(TaskRecord(**_task_kwargs(status="blocked", blocked_reason="Waiting on parts.")))
    await db_session.flush()  # should not raise


async def test_recurring_template_requires_rule(db_session: AsyncSession) -> None:
    db_session.add(TaskRecord(**_task_kwargs(is_recurring_template=True, recurrence_rule=None)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_recurring_template_with_rule_is_accepted(db_session: AsyncSession) -> None:
    db_session.add(
        TaskRecord(
            **_task_kwargs(
                is_recurring_template=True, recurrence_rule={"frequency": "daily", "interval": 1}
            )
        )
    )
    await db_session.flush()  # should not raise
