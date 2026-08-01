"""Complaint <-> Communication Hub conversation linking — every complaint
gets a backing Conversation staff can work directly in, reusing the same
get-or-create-by-linked-record helper `app.communications.integrations`
already established for reservations/orders rather than duplicating
conversation-creation logic (CLAUDE.md section 23: "Human handoff is not a
separate Communication Hub feature; assigned staff work directly in
conversations").
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.integrations import _default_channel, _get_or_create_linked_conversation
from app.db.models import Complaint


async def link_complaint_conversation(
    session: AsyncSession, *, complaint: Complaint
) -> uuid.UUID | None:
    if complaint.conversation_id is not None:
        return complaint.conversation_id

    channel = await _default_channel(session, code="internal")
    if channel is None:
        return None

    conversation = await _get_or_create_linked_conversation(
        session,
        channel=channel,
        customer_id=complaint.customer_id,
        linked_type="complaint",
        linked_id=complaint.id,
    )
    complaint.conversation_id = conversation.id
    return conversation.id
