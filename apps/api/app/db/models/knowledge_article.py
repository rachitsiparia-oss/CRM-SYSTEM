import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 13.2 sketches "documents" with a `status`
# column and no enumerated values — this phase's own instruction names an
# explicit review/approval lifecycle, which is genuinely new schema design
# (the same situation Phase 8 was in for recipes/wastage).
ARTICLE_TYPES = (
    "sop",
    "policy",
    "procedure",
    "checklist",
    "guide",
    "troubleshooting",
    "training_material",
    "emergency_instruction",
    "announcement",
)

ARTICLE_STATUSES = (
    "draft",
    "in_review",
    "changes_requested",
    "approved",
    "published",
    "superseded",
    "archived",
)

# Normalized per-scope enforcement lives in `app.knowledge.visibility`.
# `department`/`role`/`specific_staff` are resolved against
# `knowledge_visibility_rules`; the other five are pure predicates over the
# requester's own department/role/permissions, needing no extra rows.
VISIBILITY_SCOPES = (
    "all_staff",
    "department",
    "role",
    "specific_staff",
    "management_only",
    "hr_only",
    "kitchen_only",
    "front_of_house_only",
)


class KnowledgeArticle(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """The live/working copy of an article's content plus its lifecycle
    state. Immutable point-in-time snapshots live in
    `KnowledgeArticleVersion`, created whenever the article is submitted
    for review — DATABASE_AND_API.md section 13.3's "no embeddings,
    pgvector, semantic search, or RAG" restriction is preserved; `search_text`
    is a plain PostgreSQL `tsvector` maintained by `app.knowledge.search`.

    `latest_version_number` is this article's own versioning counter,
    deliberately distinct from `AuditedMixin.version` (optimistic
    concurrency) — the two count different things and must not collide.
    """

    __tablename__ = "knowledge_articles"
    __table_args__ = (
        CheckConstraint(f"article_type IN {ARTICLE_TYPES!r}", name="valid_article_type"),
        CheckConstraint(f"status IN {ARTICLE_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            f"visibility_scope IN {VISIBILITY_SCOPES!r}", name="valid_visibility_scope"
        ),
        Index("ix_knowledge_articles_category_id", "category_id"),
        Index("ix_knowledge_articles_status", "status"),
        Index("ix_knowledge_articles_owner_staff_id", "owner_staff_id"),
        Index("ix_knowledge_articles_department_id", "department_id"),
        Index("ix_knowledge_articles_search_text", "search_text", postgresql_using="gin"),
    )

    article_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    article_type: Mapped[str] = mapped_column(String(32), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_categories.id"), nullable=True
    )
    owner_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    visibility_scope: Mapped[str] = mapped_column(String(32), nullable=False, default="all_staff")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    latest_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_article_versions.id"), nullable=True
    )
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_reading_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_acknowledgement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    search_text: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
