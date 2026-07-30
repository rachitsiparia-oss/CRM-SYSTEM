import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

TEMPLATE_CATEGORIES = (
    "reservation_confirmation",
    "reservation_reminder",
    "reservation_cancellation",
    "reservation_modification",
    "waitlist_update",
    "table_ready",
    "order_confirmation",
    "order_ready",
    "order_cancellation",
    "feedback_request",
    "lead_follow_up",
    "birthday",
    "anniversary",
    "general",
)

TEMPLATE_STATUSES = ("draft", "active", "archived")


class MessageTemplate(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """DATABASE_AND_API.md section 12.4. No separate
    `message_template_versions` table — `version` (from `AuditedMixin`) is
    optimistic concurrency only; a template edit does not need its own
    historical row because every message this template ever produced keeps
    its own rendered snapshot (`Message.body_text` +
    `Message.rendered_template_variables`), which is what auditability
    actually requires (this phase's own instruction: "store the rendered
    content actually sent")."""

    __tablename__ = "message_templates"
    __table_args__ = (
        CheckConstraint(f"category IN {TEMPLATE_CATEGORIES!r}", name="valid_category"),
        CheckConstraint(f"status IN {TEMPLATE_STATUSES!r}", name="valid_status"),
        Index("ix_message_templates_channel_id", "channel_id"),
        Index("ix_message_templates_category", "category"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    provider_template_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_transactional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
