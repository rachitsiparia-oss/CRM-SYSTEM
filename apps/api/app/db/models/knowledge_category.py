import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeCategory(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """PROJECT_PLAN.md section "Scope — Knowledge Base" (folders); this
    phase's own instruction elaborates folders into hierarchical
    categories. Cycle prevention (a category cannot become its own
    ancestor) is enforced in `app.knowledge.categories`, not the database —
    a CHECK constraint cannot walk an arbitrary-depth ancestor chain.
    """

    __tablename__ = "knowledge_categories"
    __table_args__ = (
        CheckConstraint("id != parent_id", name="valid_parent_not_self"),
        Index("ix_knowledge_categories_parent_id", "parent_id"),
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
