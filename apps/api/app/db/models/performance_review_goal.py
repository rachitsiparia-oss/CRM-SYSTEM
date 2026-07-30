import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

GOAL_STATUSES = ("open", "in_progress", "achieved", "missed")


class PerformanceReviewGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "performance_review_goals"
    __table_args__ = (
        CheckConstraint(f"status IN {GOAL_STATUSES!r}", name="valid_status"),
        Index("ix_performance_review_goals_review_id", "review_id"),
    )

    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("performance_reviews.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
