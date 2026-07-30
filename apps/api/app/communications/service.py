"""Conversation and message core service — creation, assignment, status
transitions, and the read-time conversation timeline. Kept out of the
router for the same reason as `app.reservations.service`.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.communications.schemas import ConversationCreateIn, InternalNoteCreateIn
from app.communications.states import (
    is_conversation_transition_allowed,
    is_message_transition_allowed,
)
from app.db.models import (
    CommunicationChannel,
    Conversation,
    ConversationAssignment,
    ConversationStatusHistory,
    Message,
    MessageStatusHistory,
    StaffUser,
)
from app.outbox.service import record_domain_event
from app.permissions.service import has_permission

# Individually-permission-gated targets — same "doing vs. approving" split
# `app.reservations.service._GATED_TRANSITIONS` and
# `app.tasks.service._GATED_TRANSITIONS` already apply; every other allowed
# transition only needs the router's base `communications.view` +
# domain-appropriate grant.
_GATED_TRANSITIONS: dict[str, str] = {
    "resolved": "communications.resolve",
    "closed": "communications.resolve",
    "open": "communications.reopen",
    "snoozed": "communications.snooze",
}


def generate_conversation_number() -> str:
    return f"CONV-{uuid.uuid4().hex[:8].upper()}"


async def get_conversation(
    session: AsyncSession, conversation_id: uuid.UUID
) -> Conversation | None:
    return await session.get(Conversation, conversation_id)


async def _get_channel_or_404(session: AsyncSession, channel_id: uuid.UUID) -> CommunicationChannel:
    channel = await session.get(CommunicationChannel, channel_id)
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Communication channel not found.")
    return channel


async def create_conversation(
    session: AsyncSession,
    *,
    actor: StaffUser,
    payload: ConversationCreateIn,
    request: Request | None = None,
) -> Conversation:
    await _get_channel_or_404(session, payload.channel_id)
    now = datetime.now(UTC)
    conversation = Conversation(
        conversation_number=generate_conversation_number(),
        channel_id=payload.channel_id,
        customer_id=payload.customer_id,
        lead_id=payload.lead_id,
        guest_name=payload.guest_name,
        phone_e164=payload.phone_e164,
        email=payload.email,
        subject=payload.subject,
        status="open",
        priority=payload.priority,
        source="staff_initiated",
        assigned_staff_id=actor.id,
        last_activity_at=now,
        created_by=actor.id,
    )
    session.add(conversation)
    await session.flush()

    session.add(
        ConversationStatusHistory(
            conversation_id=conversation.id,
            previous_status=None,
            new_status="open",
            actor_id=actor.id,
        )
    )
    session.add(
        ConversationAssignment(
            conversation_id=conversation.id,
            previous_assignee_id=None,
            new_assignee_id=actor.id,
            actor_id=actor.id,
            reason="Assigned to creating staff member.",
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="communications.conversation.create",
        target_type="conversation",
        target_id=conversation.id,
        request=request,
        safe_metadata={"conversation_number": conversation.conversation_number},
    )
    await record_domain_event(
        session,
        event_type="communication.conversation.created",
        aggregate_type="conversation",
        aggregate_id=conversation.id,
        payload={"conversation_number": conversation.conversation_number},
    )
    await session.flush()
    return conversation


async def transition_conversation_status(
    session: AsyncSession,
    *,
    actor: StaffUser,
    conversation: Conversation,
    target_status: str,
    reason: str | None = None,
    snoozed_until: datetime | None = None,
    spam_reason: str | None = None,
    request: Request | None = None,
) -> Conversation:
    if not is_conversation_transition_allowed(conversation.status, target_status):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot move a conversation from {conversation.status!r} to {target_status!r}.",
        )
    previous_status = conversation.status
    # "open" only needs the stronger `.reopen` grant when it resurrects a
    # conversation out of a terminal-ish state; the far more common
    # pending/waiting_on_*/snoozed -> open move is ordinary traffic already
    # covered by the router's base `communications.view` + assignment/reply
    # grants.
    required_permission = _GATED_TRANSITIONS.get(target_status)
    if target_status == "open" and previous_status not in ("resolved", "closed", "spam"):
        required_permission = None
    if required_permission is not None and not await has_permission(
        session, actor.id, required_permission
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to move a conversation to {target_status!r}.",
        )
    conversation.status = target_status
    now = datetime.now(UTC)
    if target_status == "resolved":
        conversation.resolved_at = now
    if target_status == "closed":
        conversation.closed_at = now
    if target_status == "snoozed":
        conversation.snoozed_until = snoozed_until
    if target_status == "spam":
        conversation.spam_reason = spam_reason
    if target_status == "open" and previous_status in ("resolved", "closed", "spam"):
        conversation.resolved_at = None
        conversation.closed_at = None

    session.add(
        ConversationStatusHistory(
            conversation_id=conversation.id,
            previous_status=previous_status,
            new_status=target_status,
            actor_id=actor.id,
            reason=reason,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="communications.conversation.transition",
        target_type="conversation",
        target_id=conversation.id,
        request=request,
        before_summary={"status": previous_status},
        after_summary={"status": target_status},
    )
    event_name = {
        "resolved": "communication.conversation.resolved",
    }.get(target_status)
    if event_name:
        await record_domain_event(
            session,
            event_type=event_name,
            aggregate_type="conversation",
            aggregate_id=conversation.id,
            payload={"status": target_status},
        )
    await session.flush()
    return conversation


async def assign_conversation(
    session: AsyncSession,
    *,
    actor: StaffUser,
    conversation: Conversation,
    assignee_id: uuid.UUID | None,
    reason: str | None = None,
    request: Request | None = None,
) -> Conversation:
    if assignee_id is not None:
        assignee = await session.get(StaffUser, assignee_id)
        if (
            assignee is None
            or assignee.deleted_at is not None
            or assignee.account_status != "active"
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Cannot assign a conversation to an inactive or missing staff member.",
            )
    previous_assignee_id = conversation.assigned_staff_id
    conversation.assigned_staff_id = assignee_id
    session.add(
        ConversationAssignment(
            conversation_id=conversation.id,
            previous_assignee_id=previous_assignee_id,
            new_assignee_id=assignee_id,
            actor_id=actor.id,
            reason=reason,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="communications.conversation.assign",
        target_type="conversation",
        target_id=conversation.id,
        request=request,
        before_summary={
            "assigned_staff_id": str(previous_assignee_id) if previous_assignee_id else None
        },
        after_summary={"assigned_staff_id": str(assignee_id) if assignee_id else None},
    )
    await record_domain_event(
        session,
        event_type="communication.conversation.assigned",
        aggregate_type="conversation",
        aggregate_id=conversation.id,
        payload={"assignee_id": str(assignee_id) if assignee_id else None},
    )
    await session.flush()
    return conversation


async def set_conversation_priority(
    session: AsyncSession, *, actor: StaffUser, conversation: Conversation, priority: str
) -> Conversation:
    conversation.priority = priority
    conversation.updated_by = actor.id
    await session.flush()
    return conversation


async def add_internal_note(
    session: AsyncSession,
    *,
    actor: StaffUser,
    conversation: Conversation,
    payload: InternalNoteCreateIn,
) -> Message:
    now = datetime.now(UTC)
    note = Message(
        conversation_id=conversation.id,
        channel_id=conversation.channel_id,
        direction="internal",
        message_type="internal_note",
        body_text=payload.body_text,
        delivery_status="created",
        created_by=actor.id,
    )
    session.add(note)
    conversation.last_activity_at = now
    await session.flush()
    session.add(
        MessageStatusHistory(
            message_id=note.id,
            previous_status=None,
            new_status="created",
            source="staff",
            actor_id=actor.id,
        )
    )
    await session.flush()
    return note


def record_message_status_transition(
    session: AsyncSession,
    *,
    message: Message,
    target_status: str,
    source: str,
    actor_id: uuid.UUID | None,
    reason: str | None = None,
) -> bool:
    """Returns False (no-op) instead of raising when the transition is not
    allowed — an out-of-order webhook is expected traffic
    (`app.communications.states`), not an error condition."""
    if not is_message_transition_allowed(message.direction, message.delivery_status, target_status):
        return False
    previous_status = message.delivery_status
    message.delivery_status = target_status
    session.add(
        MessageStatusHistory(
            message_id=message.id,
            previous_status=previous_status,
            new_status=target_status,
            source=source,
            actor_id=actor_id,
            reason=reason,
        )
    )
    return True


async def get_conversation_timeline(
    session: AsyncSession, conversation_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Read-time union of messages + status history + assignment history —
    this phase's own deviations note explains why there is no stored
    `conversation_timeline_events` table (mirrors the read-time
    Customer-360 aggregation pattern Phase 9 already established)."""
    messages = (
        await session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
    ).all()
    status_events = (
        await session.scalars(
            select(ConversationStatusHistory)
            .where(ConversationStatusHistory.conversation_id == conversation_id)
            .order_by(ConversationStatusHistory.created_at)
        )
    ).all()
    assignment_events = (
        await session.scalars(
            select(ConversationAssignment)
            .where(ConversationAssignment.conversation_id == conversation_id)
            .order_by(ConversationAssignment.created_at)
        )
    ).all()

    entries: list[dict[str, Any]] = []
    for m in messages:
        entries.append(
            {
                "entry_type": "message",
                "occurred_at": m.created_at,
                "payload": {
                    "message_id": str(m.id),
                    "direction": m.direction,
                    "message_type": m.message_type,
                    "delivery_status": m.delivery_status,
                    "body_text": m.body_text,
                },
            }
        )
    for s in status_events:
        entries.append(
            {
                "entry_type": "status_change",
                "occurred_at": s.created_at,
                "payload": {
                    "previous_status": s.previous_status,
                    "new_status": s.new_status,
                    "reason": s.reason,
                },
            }
        )
    for a in assignment_events:
        entries.append(
            {
                "entry_type": "assignment_change",
                "occurred_at": a.created_at,
                "payload": {
                    "previous_assignee_id": str(a.previous_assignee_id)
                    if a.previous_assignee_id
                    else None,
                    "new_assignee_id": str(a.new_assignee_id) if a.new_assignee_id else None,
                    "reason": a.reason,
                },
            }
        )
    entries.sort(key=lambda e: e["occurred_at"])
    return entries
