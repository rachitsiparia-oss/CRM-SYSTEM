from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.windows import ResolvedWindow
from app.db.models import Lead

_CLOSED_STATUSES = ("won", "lost", "closed")


async def new_leads(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.deleted_at.is_(None),
            Lead.created_at >= window.start,
            Lead.created_at < window.end,
        )
    )
    return int(value or 0)


async def open_leads(session: AsyncSession, window: ResolvedWindow) -> int:
    """Point-in-time gauge as of the window's end boundary — matching
    `open_high_severity_complaints`'s own snapshot convention."""
    value = await session.scalar(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.deleted_at.is_(None),
            Lead.status.not_in(_CLOSED_STATUSES),
            Lead.created_at < window.end,
        )
    )
    return int(value or 0)


async def conversion_rate_pct(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    """Won leads among leads created within the window — a cohort
    conversion rate, GROWTH_AND_INTELLIGENCE.md section 13.8's "conversion
    rate." A lead created near the window's end may not have had time to
    convert yet; this is disclosed as a known limitation in
    DATABASE_AND_API.md's Phase 14 notes, not silently smoothed over."""
    created = await new_leads(session, window)
    if created == 0:
        return Decimal(0)
    won = await session.scalar(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.deleted_at.is_(None),
            Lead.status == "won",
            Lead.created_at >= window.start,
            Lead.created_at < window.end,
        )
    )
    return (Decimal(won or 0) / Decimal(created)) * Decimal(100)
