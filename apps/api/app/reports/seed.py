"""Idempotent development seed data — canonical system report definitions
covering the domains this phase's metric registry actually implements.
Constructed directly (not via `app.reports.service.create_report_definition`,
which always sets `definition_type="custom"`) since these are
`definition_type="system"` templates owned by the privileged seed actor
for schedule-execution purposes, but visible to every `reports.view`
holder — matching `ReportDefinition.visibility == "system"`'s own rule.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReportDefinition, StaffUser

_SYSTEM_DEFINITIONS = (
    {
        "code": "system-executive-overview",
        "name": "Executive Overview",
        "description": (
            "Net sales, completed orders, average order value, new customers, and "
            "open high-severity complaints."
        ),
        "domain": "executive",
        "metric_codes": [
            "exec_net_sales",
            "exec_completed_orders",
            "exec_average_order_value",
            "exec_new_customers",
            "exec_open_high_severity_complaints",
        ],
    },
    {
        "code": "system-sales-summary",
        "name": "Sales Summary",
        "description": (
            "Gross item value, discounts, completed and cancelled order counts, "
            "and average order value."
        ),
        "domain": "sales",
        "metric_codes": [
            "sales_gross_item_value",
            "sales_discounts",
            "sales_completed_order_count",
            "sales_cancelled_order_count",
            "sales_average_order_value",
        ],
    },
    {
        "code": "system-inventory-health",
        "name": "Inventory Health",
        "description": "Low-stock and critical-stock item counts, and waste value.",
        "domain": "inventory_suppliers",
        "metric_codes": [
            "inventory_low_stock_items",
            "inventory_critical_stock_items",
            "inventory_waste_value",
        ],
    },
    {
        "code": "system-experience-summary",
        "name": "Experience Summary",
        "description": (
            "Feedback rating and response rate, complaint rate, and average resolution time."
        ),
        "domain": "feedback",
        "metric_codes": [
            "feedback_average_rating",
            "feedback_response_rate",
            "complaints_rate",
            "complaints_average_resolution_minutes",
        ],
    },
)


async def seed_report_definitions(session: AsyncSession) -> None:
    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    if actor is None:
        return

    for entry in _SYSTEM_DEFINITIONS:
        existing = await session.scalar(
            select(ReportDefinition).where(ReportDefinition.code == entry["code"])
        )
        if existing is not None:
            continue
        session.add(
            ReportDefinition(
                code=entry["code"],
                name=entry["name"],
                description=entry["description"],
                domain=entry["domain"],
                definition_type="system",
                metric_codes=entry["metric_codes"],
                default_window="current_month",
                comparison_enabled=True,
                owner_staff_id=actor.id,
                visibility="system",
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
    await session.flush()
