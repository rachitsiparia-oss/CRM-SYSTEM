"""Daily historical time-series construction for forecasting — a
fundamentally different data need from `app.analytics_core`'s single-
window metric queries (a forecast needs many consecutive daily points, not
one aggregate), so this calls the same per-day windowing technique
`app.anomalies.engine` already uses, plus two forecast-only series
(reservation covers, inventory consumption) that don't fit the single-
aggregate metric shape cleanly enough to belong in the main registry.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.registry import METRIC_CODES, get_metric
from app.analytics_core.windows import resolve_window
from app.db.models import Reservation, StockMovement

SPECIAL_SERIES_CODES = ("reservation_covers_total", "inventory_consumption_total")


async def _reservation_covers_for_day(session: AsyncSession, *, days_ago: int) -> Decimal:
    reference = datetime.now(UTC) - timedelta(days=days_ago)
    window = resolve_window("today", now=reference)
    value = await session.scalar(
        select(func.coalesce(func.sum(Reservation.party_size), 0)).where(
            Reservation.status.in_(("arrived", "seated", "completed")),
            Reservation.created_at >= window.start,
            Reservation.created_at < window.end,
        )
    )
    return Decimal(value or 0)


async def _inventory_consumption_for_day(session: AsyncSession, *, days_ago: int) -> Decimal:
    reference = datetime.now(UTC) - timedelta(days=days_ago)
    window = resolve_window("today", now=reference)
    value = await session.scalar(
        select(func.coalesce(func.sum(-StockMovement.quantity_delta), 0)).where(
            StockMovement.movement_type == "order_consumption",
            StockMovement.occurred_at >= window.start,
            StockMovement.occurred_at < window.end,
        )
    )
    return Decimal(value or 0)


def is_valid_target_metric(target_metric_code: str) -> bool:
    return target_metric_code in SPECIAL_SERIES_CODES or target_metric_code in METRIC_CODES


async def get_daily_history(
    session: AsyncSession, target_metric_code: str, *, num_days: int
) -> list[Decimal]:
    """Returns `num_days` values, oldest first, ending yesterday (today is
    excluded — an in-progress day is not a completed historical point)."""
    if target_metric_code == "reservation_covers_total":
        values = [
            await _reservation_covers_for_day(session, days_ago=d) for d in range(num_days, 0, -1)
        ]
        return values
    if target_metric_code == "inventory_consumption_total":
        values = [
            await _inventory_consumption_for_day(session, days_ago=d)
            for d in range(num_days, 0, -1)
        ]
        return values

    metric = get_metric(target_metric_code)
    values = []
    for days_ago in range(num_days, 0, -1):
        reference = datetime.now(UTC) - timedelta(days=days_ago)
        window = resolve_window("today", now=reference)
        value = await metric.calculator(session, window)
        values.append(Decimal(value))
    return values
