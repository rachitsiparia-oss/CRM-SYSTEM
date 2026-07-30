"""Idempotent development seed data for the Communication Hub, Operational
Tasks, and Notifications — no canonical fixture for any of these exists in
PROJECT_PLAN.md (unlike the restaurant profile/menu/inventory fixtures),
so this seed is limited to reference data (channels, common templates) plus
a small number of clearly-example conversations/messages/tasks/notifications
tied to already-seeded customers/staff, the same "sample data only if
consistent with project conventions" treatment `app.reservations.seed`
gives its own example records. Every channel's `provider` is
`internal_mock` — CLAUDE.md section 16 forbids claiming a real WhatsApp/
email integration is active without verified credentials, and none exist
yet (see the Phase 10 deviations note).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.consent import get_or_create_preference
from app.communications.messaging import send_message
from app.communications.schemas import (
    ConversationCreateIn,
    MessageTemplateCreateIn,
    TemplateCategory,
)
from app.communications.service import create_conversation, transition_conversation_status
from app.communications.templates import create_template
from app.db.models import (
    CommunicationChannel,
    Customer,
    Message,
    MessageStatusHistory,
    MessageTemplate,
    StaffUser,
    TaskAssignment,
    TaskRecord,
    TaskStatusHistory,
)
from app.notifications.service import notify

_CHANNELS: tuple[tuple[str, str, bool, bool], ...] = (
    # code, name, requires_template, business_hours_restricted
    ("internal", "Internal", False, False),
    ("email", "Email", False, False),
    ("sms", "SMS", False, False),
    ("whatsapp", "WhatsApp", True, False),
    ("voice_log", "Voice Call Log", False, False),
    ("web_chat", "Website Chat", False, True),
    ("manual_call", "Manual Phone Call", False, False),
)

_TEMPLATES: tuple[tuple[str, str, str, TemplateCategory, str, list[str], bool], ...] = (
    (
        "Reservation Confirmation",
        "reservation_confirmation",
        "whatsapp",
        "reservation_confirmation",
        "Hi {customer_name}, your table for {party_size} on {reservation_date} at "
        "{reservation_time} is confirmed. Reservation {reservation_number}. — RKPR",
        [
            "customer_name",
            "party_size",
            "reservation_date",
            "reservation_time",
            "reservation_number",
        ],
        True,
    ),
    (
        "Reservation Reminder",
        "reservation_reminder",
        "whatsapp",
        "reservation_reminder",
        "Hi {customer_name}, a reminder for your reservation today at {reservation_time}. "
        "See you soon! — RKPR",
        ["customer_name", "reservation_time"],
        True,
    ),
    (
        "Reservation Cancellation",
        "reservation_cancellation",
        "whatsapp",
        "reservation_cancellation",
        "Hi {customer_name}, your reservation {reservation_number} has been cancelled.",
        ["customer_name", "reservation_number"],
        True,
    ),
    (
        "Order Confirmation",
        "order_confirmation",
        "whatsapp",
        "order_confirmation",
        "Hi, your order {order_number} has been confirmed and is being prepared. — RKPR",
        ["order_number"],
        True,
    ),
    (
        "Order Ready",
        "order_ready",
        "whatsapp",
        "order_ready",
        "Your order {order_number} is ready!",
        ["order_number"],
        True,
    ),
    (
        "Feedback Request",
        "feedback_request",
        "email",
        "feedback_request",
        "Thanks for dining with us! We'd love your feedback: {feedback_link}",
        ["feedback_link"],
        False,
    ),
    (
        "Lead Follow-Up",
        "lead_follow_up",
        "internal",
        "lead_follow_up",
        "Following up on your enquiry — how can we help, {customer_name}?",
        ["customer_name"],
        False,
    ),
)


async def seed_communication_channels(session: AsyncSession) -> None:
    for code, name, requires_template, business_hours_restricted in _CHANNELS:
        stmt = (
            pg_insert(CommunicationChannel)
            .values(
                id=uuid.uuid4(),
                code=code,
                name=name,
                provider="internal_mock",
                is_enabled=True,
                inbound_enabled=True,
                outbound_enabled=True,
                requires_template=requires_template,
                business_hours_restricted=business_hours_restricted,
            )
            .on_conflict_do_nothing(index_elements=["code"])
        )
        await session.execute(stmt)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return actor


async def seed_message_templates(session: AsyncSession) -> None:
    channel_ids = {
        row.code: row.id
        for row in (
            await session.execute(select(CommunicationChannel.code, CommunicationChannel.id))
        ).all()
    }
    for name, code, channel_code, category, body, variables, is_transactional in _TEMPLATES:
        existing = await session.scalar(select(MessageTemplate).where(MessageTemplate.code == code))
        if existing is not None:
            continue
        actor = await _system_actor(session)
        if actor is None:
            return
        template = await create_template(
            session,
            actor=actor,
            payload=MessageTemplateCreateIn(
                name=name,
                code=code,
                channel_id=channel_ids[channel_code],
                category=category,
                body=body,
                variables=variables,
                is_transactional=is_transactional,
            ),
        )
        template.status = "active"
        await session.flush()


async def seed_sample_conversations(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return
    whatsapp_channel_id = await session.scalar(
        select(CommunicationChannel.id).where(CommunicationChannel.code == "whatsapp")
    )
    if whatsapp_channel_id is None:
        return

    sample_customer = await session.scalar(select(Customer).limit(1))
    if sample_customer is None:
        return

    await get_or_create_preference(session, customer_id=sample_customer.id)

    existing = await session.scalar(
        select(Message).where(Message.body_text == "Welcome! How can we help you today?")
    )
    if existing is not None:
        return  # already seeded

    conversation = await create_conversation(
        session,
        actor=actor,
        payload=ConversationCreateIn(
            channel_id=whatsapp_channel_id,
            customer_id=sample_customer.id,
            subject="General enquiry",
        ),
    )
    channel = await session.get(CommunicationChannel, whatsapp_channel_id)
    assert channel is not None
    await send_message(
        session,
        conversation=conversation,
        channel=channel,
        recipient_reference=sample_customer.primary_phone_e164,
        body_text="Welcome! How can we help you today?",
        actor=actor,
    )
    inbound_message = Message(
        conversation_id=conversation.id,
        channel_id=whatsapp_channel_id,
        direction="inbound",
        message_type="whatsapp",
        sender_reference=sample_customer.primary_phone_e164 or "+919800000000",
        body_text="Do you have vegan options?",
        delivery_status="received",
        received_at=datetime.now(UTC) - timedelta(hours=2),
    )
    session.add(inbound_message)
    await session.flush()
    session.add(
        MessageStatusHistory(
            message_id=inbound_message.id,
            previous_status=None,
            new_status="received",
            source="webhook",
        )
    )
    conversation.last_inbound_at = inbound_message.received_at
    conversation.last_activity_at = inbound_message.received_at
    conversation.unread_count += 1
    await transition_conversation_status(
        session, actor=actor, conversation=conversation, target_status="waiting_on_staff"
    )
    await session.flush()


async def seed_sample_tasks(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return
    existing = await session.scalar(select(TaskRecord).where(TaskRecord.title == "Restock napkins"))
    if existing is not None:
        return

    now = datetime.now(UTC)
    samples = (
        ("Restock napkins", "manual", "normal", now + timedelta(days=1), "open"),
        ("Follow up with VIP guest", "lead_followup", "high", now - timedelta(hours=3), "open"),
        ("Deep-clean fryer", "system", "normal", now + timedelta(days=3), "blocked"),
    )
    for title, source, priority, due_at, target_status in samples:
        task = TaskRecord(
            task_number=f"TASK-{uuid.uuid4().hex[:8].upper()}",
            title=title,
            source=source,
            priority=priority,
            status="open",
            due_at=due_at,
            assigned_staff_id=actor.id,
            created_by=actor.id,
        )
        session.add(task)
        await session.flush()
        session.add(
            TaskStatusHistory(
                task_id=task.id, previous_status=None, new_status="open", actor_id=actor.id
            )
        )
        session.add(
            TaskAssignment(
                task_id=task.id,
                previous_assignee_id=None,
                new_assignee_id=actor.id,
                actor_id=actor.id,
            )
        )
        if target_status == "blocked":
            task.status = "blocked"
            task.blocked_reason = "Waiting on replacement part."
            session.add(
                TaskStatusHistory(
                    task_id=task.id,
                    previous_status="open",
                    new_status="blocked",
                    actor_id=actor.id,
                    reason="Waiting on replacement part.",
                )
            )
        await session.flush()

    await notify(
        session,
        notification_type="task.assigned",
        title="Sample task notification",
        record_type="task",
        record_id=task.id,
        recipient_staff_id=actor.id,
        dedup_key="seed:sample-task-notification",
    )


async def seed_communications(session: AsyncSession) -> None:
    await seed_communication_channels(session)
    await seed_message_templates(session)
    await seed_sample_conversations(session)
    await seed_sample_tasks(session)
