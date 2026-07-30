import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

# Polymorphic — same tradeoff as `ConversationLink.linked_type`/`linked_id`
# and `TaskRecord.related_type`/`related_id`. `training_course` is included
# here rather than a separate `training_course_articles` join table (this
# phase's own instruction's Training Catalogue "Linked knowledge articles"
# field), since it is the same "an article relates to some other record"
# relationship this table already exists to hold.
RELATED_TYPES = (
    "knowledge_article",
    "menu_item",
    "inventory_item",
    "reservation_policy",
    "order_workflow",
    "training_course",
    "operational_task",
)


class KnowledgeArticleRelation(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Related articles and cross-module operational references — this
    phase's own instruction sections 6 and 32."""

    __tablename__ = "knowledge_article_relations"
    __table_args__ = (
        CheckConstraint(f"related_type IN {RELATED_TYPES!r}", name="valid_related_type"),
        CheckConstraint(
            "related_type != 'knowledge_article' OR related_id != article_id",
            name="no_self_relation",
        ),
        UniqueConstraint(
            "article_id", "related_type", "related_id", name="uq_knowledge_article_relations"
        ),
        Index("ix_knowledge_article_relations_article_id", "article_id"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_articles.id"), nullable=False
    )
    related_type: Mapped[str] = mapped_column(String(32), nullable=False)
    related_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    relation_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
