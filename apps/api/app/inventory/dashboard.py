"""Inventory dashboard aggregation — every figure is a database-side
aggregate (CLAUDE.md section 5.3: "Use database-side aggregation for
dashboard metrics... Never send raw massive datasets to the chart
library"), the same convention `app.orders.service.get_dashboard_stats`
already established in Phase 7.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    InventoryBatch,
    InventoryItem,
    StockCount,
    StockReceipt,
    StockTransfer,
    WastageRecord,
)
from app.inventory.schemas import InventoryDashboardStatsOut

# CLAUDE.md section 7: business-day boundaries use the restaurant's
# configured timezone, not UTC midnight — matching Phase 7's own dashboard.
_RESTAURANT_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _today_range_utc() -> tuple[datetime, datetime]:
    now_local = datetime.now(_RESTAURANT_TIMEZONE)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(UTC), (start_local + timedelta(days=1)).astimezone(UTC)


async def get_dashboard_stats(session: AsyncSession) -> InventoryDashboardStatsOut:
    start_utc, end_utc = _today_range_utc()
    today: date = datetime.now(_RESTAURANT_TIMEZONE).date()
    soon = today + timedelta(days=7)

    active_items_filter = (InventoryItem.deleted_at.is_(None), InventoryItem.is_active.is_(True))

    total_active_items = (
        await session.scalar(
            select(func.count()).select_from(InventoryItem).where(*active_items_filter)
        )
    ) or 0

    total_stock_value = (
        await session.scalar(
            select(
                func.coalesce(
                    func.sum(
                        InventoryItem.current_stock
                        * func.coalesce(
                            InventoryItem.standard_cost_minor,
                            InventoryItem.latest_purchase_cost_minor,
                            0,
                        )
                    ),
                    0,
                )
            ).where(*active_items_filter)
        )
    ) or Decimal(0)

    low_stock_count = (
        await session.scalar(
            select(func.count())
            .select_from(InventoryItem)
            .where(*active_items_filter, InventoryItem.stock_status == "low_stock")
        )
    ) or 0
    critical_stock_count = (
        await session.scalar(
            select(func.count())
            .select_from(InventoryItem)
            .where(*active_items_filter, InventoryItem.stock_status == "critical_stock")
        )
    ) or 0
    out_of_stock_count = (
        await session.scalar(
            select(func.count())
            .select_from(InventoryItem)
            .where(*active_items_filter, InventoryItem.stock_status == "out_of_stock")
        )
    ) or 0

    active_batch_filter = (
        InventoryBatch.status == "active",
        InventoryBatch.remaining_quantity > 0,
    )
    expiring_batches_7d = (
        await session.scalar(
            select(func.count())
            .select_from(InventoryBatch)
            .where(
                *active_batch_filter,
                InventoryBatch.expires_at.is_not(None),
                InventoryBatch.expires_at >= today,
                InventoryBatch.expires_at <= soon,
            )
        )
    ) or 0
    expired_batches = (
        await session.scalar(
            select(func.count())
            .select_from(InventoryBatch)
            .where(
                *active_batch_filter,
                InventoryBatch.expires_at.is_not(None),
                InventoryBatch.expires_at < today,
            )
        )
    ) or 0

    wastage_row = (
        await session.execute(
            select(
                func.count(), func.coalesce(func.sum(WastageRecord.value_impact_minor), 0)
            ).where(WastageRecord.created_at >= start_utc, WastageRecord.created_at < end_utc)
        )
    ).one()

    receipts_today_count = (
        await session.scalar(
            select(func.count())
            .select_from(StockReceipt)
            .where(
                StockReceipt.status == "posted",
                StockReceipt.posted_at >= start_utc,
                StockReceipt.posted_at < end_utc,
            )
        )
    ) or 0
    transfers_in_progress = (
        await session.scalar(
            select(func.count()).select_from(StockTransfer).where(StockTransfer.status == "draft")
        )
    ) or 0
    pending_stock_counts = (
        await session.scalar(
            select(func.count())
            .select_from(StockCount)
            .where(StockCount.status.in_(("draft", "in_progress", "submitted")))
        )
    ) or 0

    return InventoryDashboardStatsOut(
        total_active_items=total_active_items,
        total_stock_value_minor=int(total_stock_value),
        low_stock_count=low_stock_count,
        critical_stock_count=critical_stock_count,
        out_of_stock_count=out_of_stock_count,
        expiring_batches_7d=expiring_batches_7d,
        expired_batches=expired_batches,
        wastage_today_count=wastage_row[0],
        wastage_today_value_minor=wastage_row[1],
        receipts_today_count=receipts_today_count,
        transfers_in_progress=transfers_in_progress,
        pending_stock_counts=pending_stock_counts,
    )
