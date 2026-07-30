import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeAcknowledgement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracked per staff member per exact article version — this phase's
    own instruction section 9: "Acknowledgement must be tied to the exact
    version viewed" and "Do not mark an article acknowledged merely
    because it was opened" (`acknowledged_at` stays NULL until the
    explicit acknowledge action, distinct from `first_opened_at`/
    `last_opened_at`/`open_count`). `revoked_at` is set by
    `app.knowledge.assignments` when a new mandatory version publishes,
    invalidating this row without deleting its history."""

    __tablename__ = "knowledge_acknowledgements"
    __table_args__ = (
        UniqueConstraint(
            "article_id", "version_id", "staff_id", name="uq_knowledge_acknowledgements"
        ),
        Index("ix_knowledge_acknowledgements_staff_id", "staff_id"),
    )

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_articles.id"), nullable=False
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_article_versions.id"), nullable=False
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    first_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    open_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
