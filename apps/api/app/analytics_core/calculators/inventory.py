from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.windows import ResolvedWindow
from app.db.models import InventoryItem, WastageRecord

_ACTIVE_ITEM = (InventoryItem.deleted_at.is_(None), InventoryItem.is_active.is_(True))


async def low_stock_items(session: AsyncSession, window: ResolvedWindow) -> int:
    """Point-in-time gauge (current derived `stock_status`, the same
    column `app.inventory.dashboard.get_dashboard_stats` reads) — stock
    level has no meaningful "within window" sum."""
    value = await session.scalar(
        select(func.count())
        .select_from(InventoryItem)
        .where(*_ACTIVE_ITEM, InventoryItem.stock_status == "low_stock")
    )
    return int(value or 0)


async def critical_stock_items(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(InventoryItem)
        .where(*_ACTIVE_ITEM, InventoryItem.stock_status == "critical_stock")
    )
    return int(value or 0)


async def waste_value_minor(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    """Wastage quantity valued at each item's average unit cost (falling
    back to standard cost), the same cost-basis preference
    `app.inventory.dashboard.get_dashboard_stats` uses for stock valuation."""
    value = await session.scalar(
        select(
            func.coalesce(
                func.sum(
                    WastageRecord.quantity
                    * func.coalesce(
                        InventoryItem.average_unit_cost_minor,
                        InventoryItem.standard_cost_minor,
                        0,
                    )
                ),
                0,
            )
        )
        .select_from(WastageRecord)
        .join(InventoryItem, InventoryItem.id == WastageRecord.inventory_item_id)
        .where(WastageRecord.created_at >= window.start, WastageRecord.created_at < window.end)
    )
    return Decimal(value) if value is not None else Decimal(0)
