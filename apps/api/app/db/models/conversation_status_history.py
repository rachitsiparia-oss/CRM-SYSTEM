import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class ConversationStatusHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only status-transition ledger — mirrors
    `ReservationStatusHistory`/`OrderStatusHistory`. Also the source used by
    the read-time conversation timeline (see the Phase 10 deviations note on
    why there is no stored `conversation_timeline_events` table)."""

    __tablename__ = "conversation_status_history"
    __table_args__ = (Index("ix_conversation_status_history_conversation_id", "conversation_id"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
