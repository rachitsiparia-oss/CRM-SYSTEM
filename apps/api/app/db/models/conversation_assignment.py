import uuid

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class ConversationAssignment(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only assignment-change ledger for a conversation — the
    `assigned_staff_id` fast pointer on `Conversation` always mirrors the
    latest row here, the same "live pointer plus ledger" split
    `RestaurantTable.status`/`TableStatusHistory` already established."""

    __tablename__ = "conversation_assignments"
    __table_args__ = (Index("ix_conversation_assignments_conversation_id", "conversation_id"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    previous_assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    new_assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
