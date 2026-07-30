import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

NOTIFICATION_PRIORITIES = ("low", "normal", "high", "urgent")

# Polymorphic — same tradeoff as `TaskRecord.related_type`. Widened in the
# Phase 11 migration (`ALTER TABLE ... DROP/ADD CONSTRAINT`) when
# `app.knowledge`/`app.staff_operations` started emitting notifications
# with a stable back-reference (this phase's own instruction section 30).
NOTIFICATION_RECORD_TYPES = (
    "reservation",
    "order",
    "lead",
    "customer",
    "conversation",
    "task",
    "inventory_item",
    "knowledge_article",
    "staff_shift",
    "leave_request",
    "staff_certification",
    "staff_document",
    "performance_review",
    "training_assignment",
    "shift_change_request",
)


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DATABASE_AND_API.md section 16.4, extended per this phase's own
    instruction: priority, dismissed/actioned state, and a `dedup_key`
    whose partial unique index is the DB-level enforcement of "avoid
    generating duplicate notifications for repeated events." No separate
    `notification_preferences` table in this phase — every staff member
    sees notifications relevant to their own assignments/permissions by
    default; per-user muting is deferred, not hidden (documented in the
    Phase 10 deviations note)."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(f"priority IN {NOTIFICATION_PRIORITIES!r}", name="valid_priority"),
        CheckConstraint(
            f"record_type IS NULL OR record_type IN {NOTIFICATION_RECORD_TYPES!r}",
            name="valid_record_type",
        ),
        Index("ix_notifications_recipient_staff_id_read_at", "recipient_staff_id", "read_at"),
        Index(
            "uq_notifications_dedup_key",
            "dedup_key",
            unique=True,
            postgresql_where=text("dedup_key IS NOT NULL"),
        ),
    )

    recipient_staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_users.id"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    record_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    record_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    dedup_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
