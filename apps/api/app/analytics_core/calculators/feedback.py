from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.calculators.sales import completed_order_count
from app.analytics_core.windows import ResolvedWindow
from app.db.models import Complaint, FeedbackEntry, FeedbackRating, ReviewRequest


async def average_rating(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    """`FeedbackEntry` itself carries no rating column — ratings are
    per-dimension rows on `FeedbackRating`; `overall` is the one dimension
    every rated entry is expected to carry (see that model's own
    docstring), so this metric averages that dimension only."""
    value = await session.scalar(
        select(func.avg(FeedbackRating.rating))
        .join(FeedbackEntry, FeedbackEntry.id == FeedbackRating.feedback_id)
        .where(
            FeedbackRating.dimension == "overall",
            FeedbackEntry.created_at >= window.start,
            FeedbackEntry.created_at < window.end,
        )
    )
    return Decimal(value) if value is not None else Decimal(0)


async def response_rate_pct(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    """Completed review requests as a share of review requests that
    reached the customer (sent, delivered, opened, or completed) within
    the window — GROWTH_AND_INTELLIGENCE.md section 13.14's "feedback
    response rate," scoped to the request-driven review workflow rather
    than unprompted feedback."""
    reached = await session.scalar(
        select(func.count())
        .select_from(ReviewRequest)
        .where(
            ReviewRequest.status.in_(("sent", "delivered", "opened", "completed")),
            ReviewRequest.created_at >= window.start,
            ReviewRequest.created_at < window.end,
        )
    )
    if not reached:
        return Decimal(0)
    completed = await session.scalar(
        select(func.count())
        .select_from(ReviewRequest)
        .where(
            ReviewRequest.status == "completed",
            ReviewRequest.created_at >= window.start,
            ReviewRequest.created_at < window.end,
        )
    )
    return (Decimal(completed or 0) / Decimal(reached)) * Decimal(100)


async def complaints_rate_pct(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    """Complaints created within the window as a share of completed
    orders in the same window — GROWTH_AND_INTELLIGENCE.md section 13.14's
    "complaint rate per relevant transaction volume," using completed
    orders as the transaction-volume basis."""
    orders = await completed_order_count(session, window)
    if orders == 0:
        return Decimal(0)
    complaints = await session.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.created_at >= window.start, Complaint.created_at < window.end)
    )
    return (Decimal(complaints or 0) / Decimal(orders)) * Decimal(100)


async def average_resolution_minutes(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    value = await session.scalar(
        select(
            func.avg(func.extract("epoch", Complaint.resolved_at - Complaint.created_at) / 60)
        ).where(
            Complaint.resolved_at.is_not(None),
            Complaint.resolved_at >= window.start,
            Complaint.resolved_at < window.end,
        )
    )
    return Decimal(value) if value is not None else Decimal(0)
