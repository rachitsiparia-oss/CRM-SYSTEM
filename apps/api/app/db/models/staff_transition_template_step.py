import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

STEP_TYPES = (
    "profile_completion",
    "document_submission",
    "policy_acknowledgement",
    "training",
    "uniform_issue",
    "department_induction",
    "system_access",
    "shadow_shift",
    "manager_signoff",
    "access_revocation",
    "asset_return",
    "handover",
    "final_shift",
    "exit_checklist",
    "other",
)


class StaffTransitionTemplateStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staff_transition_template_steps"
    __table_args__ = (
        CheckConstraint(f"step_type IN {STEP_TYPES!r}", name="valid_step_type"),
        UniqueConstraint("template_id", "step_order", name="uq_staff_transition_template_steps"),
        Index("ix_staff_transition_template_steps_template_id", "template_id"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_transition_templates.id"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False)
    depends_on_step_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_transition_template_steps.id"), nullable=True
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    related_knowledge_article_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_articles.id"), nullable=True
    )
