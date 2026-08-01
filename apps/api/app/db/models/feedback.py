import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    AppendOnlyTimestampMixin,
    AuditedMixin,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

# GROWTH_AND_INTELLIGENCE.md section 11.2/11.3.
FEEDBACK_SOURCES = (
    "post_order",
    "post_reservation",
    "website",
    "whatsapp",
    "email",
    "manual_entry",
    "public_review_reference",
    "campaign",
)
FEEDBACK_STATUSES = (
    "new",
    "acknowledged",
    "under_review",
    "action_required",
    "resolved",
    "closed",
    "spam",
)
FEEDBACK_PRIORITIES = ("low", "normal", "high", "urgent")
# Shared with Complaint.customer_sentiment (section 12.3) — one controlled
# vocabulary, staff-selected or deterministically derived, never requiring
# the Phase-14-gated AI sentiment classifier this phase's own section 11.9
# describes as advisory-only and not required for completion.
SENTIMENT_LABELS = ("positive", "neutral", "negative", "mixed")
# section 11.5's ten rating dimensions.
RATING_DIMENSIONS = (
    "overall",
    "food_quality",
    "taste",
    "packaging",
    "delivery",
    "speed",
    "staff_service",
    "cleanliness",
    "reservation_experience",
    "value",
)


class FeedbackEntry(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """GROWTH_AND_INTELLIGENCE.md section 11.2-11.4.

    `customer_id` is nullable — feedback may arrive from a guest with no
    customer record yet (e.g. a public review reference or a walk-in
    comment card); `guest_name`/`guest_contact` capture identity in that
    case. `converted_to_complaint_id` is populated by
    `app.feedback.service.convert_to_complaint` and constrained via a
    deferred `ALTER TABLE` in the migration (added after `complaints`
    exists) since the two tables reference each other.
    """

    __tablename__ = "feedback_entries"
    __table_args__ = (
        CheckConstraint(f"source IN {FEEDBACK_SOURCES!r}", name="valid_source"),
        CheckConstraint(f"status IN {FEEDBACK_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"priority IN {FEEDBACK_PRIORITIES!r}", name="valid_priority"),
        CheckConstraint(
            f"sentiment IS NULL OR sentiment IN {SENTIMENT_LABELS!r}", name="valid_sentiment"
        ),
        CheckConstraint(
            "customer_id IS NOT NULL OR guest_name IS NOT NULL OR guest_contact IS NOT NULL",
            name="requires_customer_or_guest_identity",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR acknowledged_at IS NULL OR resolved_at >= acknowledged_at",
            name="valid_resolution_ordering",
        ),
        Index("ix_feedback_entries_customer_id", "customer_id"),
        Index("ix_feedback_entries_status", "status"),
        Index("ix_feedback_entries_order_id", "order_id"),
        Index("ix_feedback_entries_reservation_id", "reservation_id"),
        Index("ix_feedback_entries_assigned_staff_id", "assigned_staff_id"),
        Index("ix_feedback_entries_created_at", "created_at"),
    )

    feedback_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    guest_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    guest_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id"), nullable=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True)
    consent_for_follow_up: Mapped[bool] = mapped_column(nullable=False, default=False)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # No FK declared here — added via ALTER TABLE in the migration once
    # `complaints` exists (see module docstring).
    converted_to_complaint_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)


class FeedbackRating(UUIDPrimaryKeyMixin, Base):
    """One row per rated dimension — section 11.5. `overall` is the one
    dimension every rated feedback entry is expected to carry; the other
    nine are optional, matching the instruction's "Dimensions may be
    optional, but overall rating... rules should be explicit"."""

    __tablename__ = "feedback_ratings"
    __table_args__ = (
        CheckConstraint(f"dimension IN {RATING_DIMENSIONS!r}", name="valid_dimension"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="valid_rating_range"),
        Index(
            "uq_feedback_ratings_entry_dimension",
            "feedback_id",
            "dimension",
            unique=True,
        ),
    )

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedback_entries.id"), nullable=False
    )
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)


class FeedbackStatusHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    __tablename__ = "feedback_status_history"
    __table_args__ = (Index("ix_feedback_status_history_feedback_id", "feedback_id"),)

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedback_entries.id"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class FeedbackTag(Base):
    """Reuses Phase 5's global `tags` table — the same junction shape
    `CustomerTag`/`KnowledgeArticleTag` already established, not a new tag
    catalogue."""

    __tablename__ = "feedback_tags"

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedback_entries.id"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id"), primary_key=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class FeedbackAttachment(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Mirrors `KnowledgeAttachment`'s private-storage-path/signed-URL
    discipline (`app.storage`, TOOLS.md section 5.3)."""

    __tablename__ = "feedback_attachments"
    __table_args__ = (
        CheckConstraint(
            "upload_status IN ('pending', 'uploaded', 'failed')", name="valid_upload_status"
        ),
        CheckConstraint(
            "scan_status IN ('pending', 'clean', 'infected', 'skipped')",
            name="valid_scan_status",
        ),
        CheckConstraint("size_bytes > 0", name="valid_size_bytes"),
        Index("ix_feedback_attachments_feedback_id", "feedback_id"),
    )

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feedback_entries.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upload_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    scan_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
