import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class TaskStatusHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only status-transition ledger, mirrors
    `ConversationStatusHistory`/`ReservationStatusHistory`."""

    __tablename__ = "task_status_history"
    __table_args__ = (Index("ix_task_status_history_task_id", "task_id"),)

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_records.id"), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
