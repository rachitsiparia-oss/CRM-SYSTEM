import uuid

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class TaskAssignment(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only assignment-change ledger, mirrors `ConversationAssignment`."""

    __tablename__ = "task_assignments"
    __table_args__ = (Index("ix_task_assignments_task_id", "task_id"),)

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_records.id"), nullable=False)
    previous_assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    new_assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
