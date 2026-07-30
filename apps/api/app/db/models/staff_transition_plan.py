import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.staff_transition_template import TRANSITION_TYPES

PLAN_STATUSES = ("in_progress", "completed", "cancelled")


class StaffTransitionPlan(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A staff member's own instantiation of a `StaffTransitionTemplate` —
    this phase's own instruction sections 15/16."""

    __tablename__ = "staff_transition_plans"
    __table_args__ = (
        CheckConstraint(f"transition_type IN {TRANSITION_TYPES!r}", name="valid_transition_type"),
        CheckConstraint(f"status IN {PLAN_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "completion_percentage BETWEEN 0 AND 100", name="valid_completion_percentage"
        ),
        Index("ix_staff_transition_plans_staff_user_id", "staff_user_id"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_transition_templates.id"), nullable=True
    )
    transition_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
