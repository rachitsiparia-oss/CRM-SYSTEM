import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class KnowledgeArticleVersion(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Immutable snapshot taken when an article is submitted for review —
    "Every material content change must create a version record"
    (this phase's own instruction). `app.knowledge.articles` never issues an
    UPDATE to a row here once `published_at` is set; there is no database
    trigger enforcing this (the same service-level-only immutability
    discipline every prior phase's status/history tables already use), but
    the invariant is real and tested.
    """

    __tablename__ = "knowledge_article_versions"
    __table_args__ = (
        UniqueConstraint("article_id", "version_number", name="uq_knowledge_article_versions"),
        Index("ix_knowledge_article_versions_article_id", "article_id"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_articles.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_snapshot: Mapped[str] = mapped_column(String(220), nullable=False)
    summary_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
