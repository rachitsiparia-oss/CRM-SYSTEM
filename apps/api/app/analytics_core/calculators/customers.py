from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.windows import ResolvedWindow
from app.db.models import Customer, LoyaltyAccount, Order


async def total(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(Customer)
        .where(Customer.deleted_at.is_(None), Customer.created_at < window.end)
    )
    return int(value or 0)


async def new(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(Customer)
        .where(
            Customer.deleted_at.is_(None),
            Customer.created_at >= window.start,
            Customer.created_at < window.end,
        )
    )
    return int(value or 0)


async def repeat_rate_pct(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    """Percentage of customers with more than one completed order within
    the window, among customers with at least one — GROWTH_AND_INTELLIGENCE.md
    section 13.7's "repeat customers" definition, using the completed-order
    count already established as this window's order-activity basis."""
    rows = (
        await session.execute(
            select(Order.customer_id, func.count())
            .where(
                Order.status == "completed",
                Order.created_at >= window.start,
                Order.created_at < window.end,
                Order.customer_id.is_not(None),
            )
            .group_by(Order.customer_id)
        )
    ).all()
    if not rows:
        return Decimal(0)
    customers_with_orders = len(rows)
    repeat_customers = sum(1 for _customer_id, count in rows if count > 1)
    return (Decimal(repeat_customers) / Decimal(customers_with_orders)) * Decimal(100)


async def loyalty_enrollment(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(LoyaltyAccount)
        .where(LoyaltyAccount.status == "active", LoyaltyAccount.created_at < window.end)
    )
    return int(value or 0)
