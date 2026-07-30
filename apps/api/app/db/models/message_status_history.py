import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

STATUS_HISTORY_SOURCES = ("system", "staff", "webhook")


class MessageStatusHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only lifecycle ledger for `Message.delivery_status` — lets
    `app.communications.states` reject an out-of-order webhook that would
    otherwise regress a message from a more advanced status to an earlier
    one (this phase's own instruction section 16)."""

    __tablename__ = "message_status_history"
    __table_args__ = (
        CheckConstraint(f"source IN {STATUS_HISTORY_SOURCES!r}", name="valid_source"),
        Index("ix_message_status_history_message_id", "message_id"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
