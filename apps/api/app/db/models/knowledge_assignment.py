import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

ASSIGNEE_TYPES = ("staff", "department", "role")
ASSIGNMENT_STATUSES = ("active", "completed", "cancelled")


class KnowledgeAssignment(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Assigns an article (optionally pinned to a specific version) to a
    staff member, department, or role — this phase's own instruction
    section 10. `version_id IS NULL` means "whatever is currently
    published." Dedup: "No duplicate active assignment for the same
    article version and staff member" is enforced by the partial unique
    index below for `staff`-type assignments."""

    __tablename__ = "knowledge_assignments"
    __table_args__ = (
        CheckConstraint(f"assignee_type IN {ASSIGNEE_TYPES!r}", name="valid_assignee_type"),
        CheckConstraint(f"status IN {ASSIGNMENT_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "(assignee_type = 'staff' AND staff_id IS NOT NULL "
            "AND department_id IS NULL AND role_id IS NULL) OR "
            "(assignee_type = 'department' AND department_id IS NOT NULL "
            "AND staff_id IS NULL AND role_id IS NULL) OR "
            "(assignee_type = 'role' AND role_id IS NOT NULL "
            "AND staff_id IS NULL AND department_id IS NULL)",
            name="valid_assignee_target",
        ),
        Index("ix_knowledge_assignments_article_id", "article_id"),
        Index(
            "uq_knowledge_assignments_active_staff",
            "article_id",
            "staff_id",
            unique=True,
            postgresql_where=text("assignee_type = 'staff' AND status = 'active'"),
        ),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_articles.id"), nullable=False
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_article_versions.id"), nullable=True
    )
    assignee_type: Mapped[str] = mapped_column(String(16), nullable=False)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
