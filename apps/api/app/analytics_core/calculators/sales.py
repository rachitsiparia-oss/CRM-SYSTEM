from decimal import Decimal

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.windows import ResolvedWindow
from app.db.models import Order


def _completed_in_window(window: ResolvedWindow) -> tuple[ColumnElement[bool], ...]:
    return (
        Order.status == "completed",
        Order.created_at >= window.start,
        Order.created_at < window.end,
    )


async def gross_item_value_minor(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.coalesce(func.sum(Order.subtotal_minor), 0)).where(
            *_completed_in_window(window)
        )
    )
    return int(value or 0)


async def net_sales_minor(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.coalesce(func.sum(Order.grand_total_minor), 0)).where(
            *_completed_in_window(window)
        )
    )
    return int(value or 0)


async def discounts_minor(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.coalesce(func.sum(Order.discount_minor), 0)).where(
            *_completed_in_window(window)
        )
    )
    return int(value or 0)


async def completed_order_count(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count()).select_from(Order).where(*_completed_in_window(window))
    )
    return int(value or 0)


async def average_order_value_minor(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    net_sales = await net_sales_minor(session, window)
    count = await completed_order_count(session, window)
    if count == 0:
        return Decimal(0)
    return Decimal(net_sales) / Decimal(count)


async def cancelled_order_count(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.status == "cancelled",
            Order.created_at >= window.start,
            Order.created_at < window.end,
        )
    )
    return int(value or 0)
