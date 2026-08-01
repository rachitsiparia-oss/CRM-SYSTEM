from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.calculators.sales import (
    average_order_value_minor as sales_average_order_value_minor,
)
from app.analytics_core.calculators.sales import (
    completed_order_count as sales_completed_order_count,
)
from app.analytics_core.calculators.sales import net_sales_minor as sales_net_sales_minor
from app.analytics_core.windows import ResolvedWindow
from app.db.models import Complaint, Customer

# Re-exported so the executive domain's metric definitions can point at
# these names directly — the executive dashboard's net sales, completed
# orders, and average order value are the *same* figures as the sales
# domain's, not a second calculation (GROWTH_AND_INTELLIGENCE.md section
# 13.4: one metric, one definition, one owner).
net_sales_minor = sales_net_sales_minor
completed_orders = sales_completed_order_count
average_order_value_minor = sales_average_order_value_minor


async def new_customers(session: AsyncSession, window: ResolvedWindow) -> int:
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


async def open_high_severity_complaints(session: AsyncSession, window: ResolvedWindow) -> int:
    """A point-in-time gauge as of the window's end boundary, not a
    within-window count — an "open complaints" figure is inherently a
    snapshot, the same convention `app.complaints.analytics.get_analytics`
    already uses for its own `open_count`."""
    value = await session.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(
            Complaint.severity.in_(("high", "critical")),
            Complaint.status.not_in(("resolved", "closed", "cancelled")),
            Complaint.created_at < window.end,
        )
    )
    return int(value or 0)
