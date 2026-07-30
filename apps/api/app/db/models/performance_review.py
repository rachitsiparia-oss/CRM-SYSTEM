import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

REVIEW_STATUSES = ("draft", "in_progress", "submitted", "reviewed", "finalized", "acknowledged")


class PerformanceReview(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """This phase's own instruction section 25. No separate
    `performance_review_cycles` table — `cycle_label`/`period_start_date`/
    `period_end_date` are a shared label and date range for a batch of
    reviews, not an entity with its own independent lifecycle, the same
    consolidation Phase 10 applied to drop `message_template_versions`.
    "Finalized reviews must not be silently edited" is enforced in
    `app.staff_operations.reviews` (a service-level guard once
    `finalized_at` is set), matching every other immutability rule in this
    codebase that isn't expressible as a single-row CHECK constraint."""

    __tablename__ = "performance_reviews"
    __table_args__ = (
        CheckConstraint(f"status IN {REVIEW_STATUSES!r}", name="valid_status"),
        CheckConstraint("period_end_date >= period_start_date", name="valid_period_range"),
        CheckConstraint(
            "overall_rating IS NULL OR overall_rating BETWEEN 1 AND 5",
            name="valid_overall_rating",
        ),
        Index("ix_performance_reviews_staff_user_id", "staff_user_id"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    cycle_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    overall_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_areas: Mapped[str | None] = mapped_column(Text, nullable=True)
    staff_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    staff_acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
