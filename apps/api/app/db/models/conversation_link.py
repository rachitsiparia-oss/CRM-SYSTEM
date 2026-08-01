import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# Polymorphic on purpose: a conversation can accumulate links to more than
# one order over its life (a repeat customer messaging about a second
# order in the same thread), which a single nullable `order_id` column on
# `Conversation` cannot represent. `linked_id` has no FK — the referenced
# table depends on `linked_type` and is validated at the service layer,
# the same polymorphic-reference tradeoff `TaskRecord.related_type`/
# `related_id` makes for the same reason. `complaint` was added in Phase 13
# (`feedback_case` already anticipated feedback linkage in Phase 10; a
# complaint is a distinct linked record, not a feedback case).
CONVERSATION_LINK_TYPES = ("reservation", "order", "waitlist_entry", "feedback_case", "complaint")


class ConversationLink(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    __tablename__ = "conversation_links"
    __table_args__ = (
        CheckConstraint(f"linked_type IN {CONVERSATION_LINK_TYPES!r}", name="valid_linked_type"),
        Index("ix_conversation_links_conversation_id", "conversation_id"),
        Index("ix_conversation_links_linked", "linked_type", "linked_id"),
        Index(
            "uq_conversation_links_active",
            "conversation_id",
            "linked_type",
            "linked_id",
            unique=True,
            postgresql_where=text("unlinked_at IS NULL"),
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    linked_type: Mapped[str] = mapped_column(String(32), nullable=False)
    linked_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unlinked_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
