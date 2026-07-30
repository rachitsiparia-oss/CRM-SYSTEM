import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

ASSIGNMENT_STATUSES = (
    "assigned",
    "in_progress",
    "completed",
    "failed",
    "overdue",
    "waived",
    "cancelled",
)


class TrainingAssignment(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """One row per staff/course — repeated tries live in
    `TrainingAttempt`; a re-assignment after failure updates `status` back
    to `assigned` rather than creating a duplicate row, per this phase's
    own instruction section 22."""

    __tablename__ = "training_assignments"
    __table_args__ = (
        CheckConstraint(f"status IN {ASSIGNMENT_STATUSES!r}", name="valid_status"),
        UniqueConstraint("course_id", "staff_user_id", name="uq_training_assignments"),
        Index("ix_training_assignments_staff_user_id", "staff_user_id"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("training_courses.id"), nullable=False)
    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="assigned")
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
