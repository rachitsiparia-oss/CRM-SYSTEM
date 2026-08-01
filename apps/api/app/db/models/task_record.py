import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# No schema for Operational Tasks exists anywhere in DATABASE_AND_API.md —
# PROJECT_PLAN.md/ROADMAP.md name it only as a Phase 10 scope bullet
# ("creation sources, assignment, priority, due time, completion evidence,
# recurring tasks"). This is genuinely new schema, designed here for the
# first time, the same situation Phase 8 was in for recipes/wastage.
TASK_SOURCES = (
    "manual",
    "reservation_followup",
    "order_issue",
    "lead_followup",
    "inventory_alert",
    "system",
    "recurring",
)

TASK_PRIORITIES = ("low", "normal", "high", "urgent")

TASK_STATUSES = ("open", "in_progress", "blocked", "completed", "cancelled")

# Polymorphic — same tradeoff as `ConversationLink.linked_type`/`linked_id`.
# The five Phase 11 values were added when `app.knowledge`/
# `app.staff_operations` started creating tasks with a stable back-
# reference (this phase's own instruction section 31); `complaint` and
# `feedback` were added the same way for Phase 13. The CHECK constraint is
# widened via `ALTER TABLE` in each owning phase's migration rather than
# duplicated as a second polymorphic column.
TASK_RELATED_TYPES = (
    "customer",
    "lead",
    "order",
    "reservation",
    "conversation",
    "inventory_item",
    "knowledge_article",
    "staff_transition_plan",
    "staff_certification",
    "staff_document",
    "training_assignment",
    "performance_review",
    "complaint",
    "feedback",
)


class TaskRecord(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Never deleted, only cancelled — mirrors `Reservation`/`Order`.
    Recurrence is embedded (`is_recurring_template`/`recurrence_rule`/
    `parent_task_id`) rather than a separate `task_recurrence_rules` table:
    a recurring task is just a template row that a generator reads and
    spawns dated instances from, which needs no independent lifecycle of
    its own beyond the template task it already is."""

    __tablename__ = "task_records"
    __table_args__ = (
        CheckConstraint(f"source IN {TASK_SOURCES!r}", name="valid_source"),
        CheckConstraint(f"priority IN {TASK_PRIORITIES!r}", name="valid_priority"),
        CheckConstraint(f"status IN {TASK_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            f"related_type IS NULL OR related_type IN {TASK_RELATED_TYPES!r}",
            name="valid_related_type",
        ),
        CheckConstraint(
            "NOT is_recurring_template OR recurrence_rule IS NOT NULL",
            name="recurring_template_requires_rule",
        ),
        CheckConstraint(
            "status != 'blocked' OR blocked_reason IS NOT NULL",
            name="blocked_requires_reason",
        ),
        Index("ix_task_records_assigned_staff_id", "assigned_staff_id"),
        Index("ix_task_records_status", "status"),
        Index("ix_task_records_due_at", "due_at"),
        Index("ix_task_records_parent_task_id", "parent_task_id"),
        Index("ix_task_records_related", "related_type", "related_id"),
        Index(
            "uq_task_records_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    task_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    related_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    is_recurring_template: Mapped[bool] = mapped_column(nullable=False, default=False)
    # `none_as_null=True` — SQLAlchemy's JSON/JSONB types otherwise coerce a
    # Python `None` into a stored JSON `null` literal rather than a SQL
    # NULL, which would silently defeat the
    # `recurring_template_requires_rule` CHECK constraint above (a JSONB
    # `null` value still satisfies `IS NOT NULL`).
    recurrence_rule: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_records.id"), nullable=True
    )
    next_occurrence_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
