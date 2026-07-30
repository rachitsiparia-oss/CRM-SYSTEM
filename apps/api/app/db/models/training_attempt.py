import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TrainingAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """This phase's own instruction section 22 — "Prevent exceeding
    maximum attempts unless an authorized reset occurs" is enforced in
    `app.staff_operations.training` against `TrainingCourse.max_attempts`,
    not by a database constraint (the limit is per-course, not fixed)."""

    __tablename__ = "training_attempts"
    __table_args__ = (
        CheckConstraint("score IS NULL OR score BETWEEN 0 AND 100", name="valid_score_bounds"),
        UniqueConstraint("assignment_id", "attempt_number", name="uq_training_attempts"),
        Index("ix_training_attempts_assignment_id", "assignment_id"),
    )

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("training_assignments.id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_pass: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    completion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
