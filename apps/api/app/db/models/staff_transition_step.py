import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.staff_transition_template_step import STEP_TYPES

STEP_STATUSES = ("pending", "in_progress", "completed", "skipped", "blocked")


class StaffTransitionStep(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    __tablename__ = "staff_transition_steps"
    __table_args__ = (
        CheckConstraint(f"step_type IN {STEP_TYPES!r}", name="valid_step_type"),
        CheckConstraint(f"status IN {STEP_STATUSES!r}", name="valid_status"),
        Index("ix_staff_transition_steps_plan_id", "plan_id"),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_transition_plans.id"), nullable=False
    )
    template_step_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_transition_template_steps.id"), nullable=True
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    completion_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    depends_on_step_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_transition_steps.id"), nullable=True
    )
