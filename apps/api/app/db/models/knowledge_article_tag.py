import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class KnowledgeArticleTag(Base):
    """Article-to-tag mapping reusing the single canonical `tags` table
    already shared by customers and reservations (`Tag` /
    `normalize_tag_name`) — no separate `knowledge_tags` table, per
    CLAUDE.md section 3's "avoid duplicating... models"."""

    __tablename__ = "knowledge_article_tags"
    __table_args__ = (
        PrimaryKeyConstraint("article_id", "tag_id", name="pk_knowledge_article_tags"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_articles.id"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id"), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
