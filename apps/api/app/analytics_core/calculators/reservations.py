from decimal import Decimal

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.windows import ResolvedWindow
from app.db.models import Reservation

_SEATED_OUTCOME_STATUSES = ("arrived", "seated", "completed")


def _in_window(window: ResolvedWindow) -> tuple[ColumnElement[bool], ...]:
    return (Reservation.created_at >= window.start, Reservation.created_at < window.end)


async def requests(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count()).select_from(Reservation).where(*_in_window(window))
    )
    return int(value or 0)


async def confirmed(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(*_in_window(window), Reservation.status == "confirmed")
    )
    return int(value or 0)


async def no_show_rate_pct(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    """No-shows as a share of reservations that reached a seated-or-later
    outcome within the window — GROWTH_AND_INTELLIGENCE.md section 13.9."""
    outcomes = await session.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(*_in_window(window), Reservation.status.in_((*_SEATED_OUTCOME_STATUSES, "no_show")))
    )
    if not outcomes:
        return Decimal(0)
    no_shows = await session.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(*_in_window(window), Reservation.status == "no_show")
    )
    return (Decimal(no_shows or 0) / Decimal(outcomes)) * Decimal(100)


async def average_party_size(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    value = await session.scalar(
        select(func.avg(Reservation.party_size)).where(*_in_window(window))
    )
    return Decimal(value) if value is not None else Decimal(0)
