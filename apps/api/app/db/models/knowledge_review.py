import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

REVIEW_ACTIONS = (
    "submitted",
    "approved",
    "changes_requested",
    "published",
    "unpublished",
    "superseded",
    "archived",
    "reopened",
)


class KnowledgeReview(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only review/approval decision history — this phase's own
    instruction section 4 ("Record review comments and decision history")."""

    __tablename__ = "knowledge_reviews"
    __table_args__ = (
        CheckConstraint(f"action IN {REVIEW_ACTIONS!r}", name="valid_action"),
        Index("ix_knowledge_reviews_article_id", "article_id"),
        Index("ix_knowledge_reviews_version_id", "version_id"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_articles.id"), nullable=False
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_article_versions.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
