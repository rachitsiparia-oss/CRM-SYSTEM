"""Deterministic, bounded feedback and review-request analytics —
instruction section 20 (not Phase 14's full reporting platform)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FeedbackEntry, FeedbackRating, ReviewRequest
from app.feedback.schemas import FeedbackAnalyticsOut, ReviewRequestAnalyticsOut


async def get_feedback_analytics(session: AsyncSession) -> FeedbackAnalyticsOut:
    since = datetime.now(UTC) - timedelta(days=30)

    total_30d = await session.scalar(
        select(func.count()).select_from(FeedbackEntry).where(FeedbackEntry.created_at >= since)
    )
    avg_overall = await session.scalar(
        select(func.avg(FeedbackRating.rating))
        .join(FeedbackEntry, FeedbackEntry.id == FeedbackRating.feedback_id)
        .where(FeedbackRating.dimension == "overall", FeedbackEntry.created_at >= since)
    )

    sentiment_result = (
        await session.execute(
            select(FeedbackEntry.sentiment, func.count())
            .where(FeedbackEntry.created_at >= since, FeedbackEntry.sentiment.is_not(None))
            .group_by(FeedbackEntry.sentiment)
        )
    ).all()
    sentiment_rows: dict[str | None, int] = {row[0]: row[1] for row in sentiment_result}
    converted_30d = await session.scalar(
        select(func.count())
        .select_from(FeedbackEntry)
        .where(
            FeedbackEntry.created_at >= since, FeedbackEntry.converted_to_complaint_id.is_not(None)
        )
    )
    by_source_rows = (
        await session.execute(
            select(FeedbackEntry.source, func.count())
            .where(FeedbackEntry.created_at >= since)
            .group_by(FeedbackEntry.source)
        )
    ).all()

    return FeedbackAnalyticsOut(
        total_30d=int(total_30d or 0),
        average_overall_rating=round(avg_overall, 2) if avg_overall is not None else None,
        positive_count_30d=int(sentiment_rows.get("positive", 0)),
        neutral_count_30d=int(sentiment_rows.get("neutral", 0)),
        negative_count_30d=int(sentiment_rows.get("negative", 0)),
        converted_to_complaint_30d=int(converted_30d or 0),
        by_source=[{"source": row[0], "count": row[1]} for row in by_source_rows],
    )


async def get_review_request_analytics(session: AsyncSession) -> ReviewRequestAnalyticsOut:
    since = datetime.now(UTC) - timedelta(days=30)

    total_30d = await session.scalar(
        select(func.count()).select_from(ReviewRequest).where(ReviewRequest.created_at >= since)
    )
    sent_30d = await session.scalar(
        select(func.count())
        .select_from(ReviewRequest)
        .where(ReviewRequest.created_at >= since, ReviewRequest.sent_at.is_not(None))
    )
    completed_30d = await session.scalar(
        select(func.count())
        .select_from(ReviewRequest)
        .where(ReviewRequest.created_at >= since, ReviewRequest.completed_at.is_not(None))
    )
    suppressed_30d = await session.scalar(
        select(func.count())
        .select_from(ReviewRequest)
        .where(ReviewRequest.created_at >= since, ReviewRequest.status == "suppressed")
    )

    total_30d = total_30d or 0
    completed_30d = completed_30d or 0
    completion_rate = completed_30d / total_30d * 100 if total_30d else 0.0

    return ReviewRequestAnalyticsOut(
        total_30d=total_30d,
        sent_30d=int(sent_30d or 0),
        completed_30d=completed_30d,
        completion_rate_pct=round(completion_rate, 1),
        suppressed_30d=int(suppressed_30d or 0),
    )
