"""The canonical metric registry — GROWTH_AND_INTELLIGENCE.md section 13.4's
metric definition contract (code, display name, business definition,
included/excluded record states, time basis, currency basis, data source,
freshness, permitted dimensions, owner, version), one `MetricDef` per
metric.

Scope note: this registry implements a substantial, representative subset
of GROWTH_AND_INTELLIGENCE.md sections 13.5-13.14's illustrative metric
lists — enough to power all ten required dashboards
(GROWTH_AND_INTELLIGENCE.md section 16) and the report builder — rather
than every metric named in those "may include" lists. The registry pattern
is designed to be extended with more metrics later without any structural
change; see `docs/DATABASE_AND_API.md`'s Phase 14 implementation notes for
the full list of what was and wasn't built.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.calculators import (
    customers as customers_calc,
)
from app.analytics_core.calculators import (
    executive as executive_calc,
)
from app.analytics_core.calculators import (
    feedback as feedback_calc,
)
from app.analytics_core.calculators import (
    inventory as inventory_calc,
)
from app.analytics_core.calculators import (
    leads as leads_calc,
)
from app.analytics_core.calculators import (
    marketing as marketing_calc,
)
from app.analytics_core.calculators import (
    reservations as reservations_calc,
)
from app.analytics_core.calculators import (
    sales as sales_calc,
)
from app.analytics_core.calculators import (
    staff as staff_calc,
)
from app.analytics_core.windows import ResolvedWindow

MetricValue = int | Decimal
MetricCalculator = Callable[[AsyncSession, ResolvedWindow], Awaitable[MetricValue]]

METRIC_VALUE_TYPES = ("count", "currency_minor", "percent", "decimal", "duration_minutes")
METRIC_FRESHNESS_STATES = ("live", "near_real_time", "cached", "scheduled")


@dataclass(frozen=True)
class MetricDef:
    code: str
    display_name: str
    description: str
    domain: str
    value_type: str
    required_permission: str
    calculation_owner: str
    calculator: MetricCalculator
    unit: str | None = None
    supports_comparison: bool = True
    freshness: str = "live"
    version: int = 1
    included_states: str = ""
    excluded_states: str = ""


def _m(
    code: str,
    display_name: str,
    description: str,
    domain: str,
    value_type: str,
    required_permission: str,
    calculation_owner: str,
    calculator: MetricCalculator,
    *,
    unit: str | None = None,
    included_states: str = "",
    excluded_states: str = "",
) -> MetricDef:
    return MetricDef(
        code=code,
        display_name=display_name,
        description=description,
        domain=domain,
        value_type=value_type,
        required_permission=required_permission,
        calculation_owner=calculation_owner,
        calculator=calculator,
        unit=unit,
        included_states=included_states,
        excluded_states=excluded_states,
    )


METRICS: tuple[MetricDef, ...] = (
    # Executive — GROWTH_AND_INTELLIGENCE.md section 13.5.
    _m(
        "exec_net_sales",
        "Net sales",
        "Sum of grand_total_minor for completed orders in the window.",
        "executive",
        "currency_minor",
        "analytics.executive.view",
        "app.analytics_core.calculators.executive",
        executive_calc.net_sales_minor,
        unit="INR_minor",
        included_states="orders.status = completed",
    ),
    _m(
        "exec_completed_orders",
        "Completed orders",
        "Count of orders with status = completed in the window.",
        "executive",
        "count",
        "analytics.executive.view",
        "app.analytics_core.calculators.executive",
        executive_calc.completed_orders,
    ),
    _m(
        "exec_average_order_value",
        "Average order value",
        "Net sales divided by completed order count in the window.",
        "executive",
        "currency_minor",
        "analytics.executive.view",
        "app.analytics_core.calculators.executive",
        executive_calc.average_order_value_minor,
        unit="INR_minor",
    ),
    _m(
        "exec_new_customers",
        "New customers",
        "Count of non-deleted customers created within the window.",
        "executive",
        "count",
        "analytics.executive.view",
        "app.analytics_core.calculators.executive",
        executive_calc.new_customers,
    ),
    _m(
        "exec_open_high_severity_complaints",
        "Open high-severity complaints",
        "Point-in-time count of high/critical complaints not resolved, "
        "closed, or cancelled, as of the window's end.",
        "executive",
        "count",
        "analytics.executive.view",
        "app.analytics_core.calculators.executive",
        executive_calc.open_high_severity_complaints,
        excluded_states="resolved, closed, cancelled",
    ),
    # Sales — GROWTH_AND_INTELLIGENCE.md section 13.6.
    _m(
        "sales_gross_item_value",
        "Gross item value",
        "Sum of subtotal_minor for completed orders in the window.",
        "sales",
        "currency_minor",
        "analytics.sales.view",
        "app.analytics_core.calculators.sales",
        sales_calc.gross_item_value_minor,
        unit="INR_minor",
    ),
    _m(
        "sales_discounts",
        "Discounts",
        "Sum of discount_minor for completed orders in the window.",
        "sales",
        "currency_minor",
        "analytics.sales.view",
        "app.analytics_core.calculators.sales",
        sales_calc.discounts_minor,
        unit="INR_minor",
    ),
    _m(
        "sales_completed_order_count",
        "Completed order count",
        "Count of orders with status = completed in the window.",
        "sales",
        "count",
        "analytics.sales.view",
        "app.analytics_core.calculators.sales",
        sales_calc.completed_order_count,
    ),
    _m(
        "sales_cancelled_order_count",
        "Cancelled order count",
        "Count of orders with status = cancelled created in the window.",
        "sales",
        "count",
        "analytics.sales.view",
        "app.analytics_core.calculators.sales",
        sales_calc.cancelled_order_count,
    ),
    _m(
        "sales_average_order_value",
        "Average order value",
        "Net sales divided by completed order count in the window.",
        "sales",
        "currency_minor",
        "analytics.sales.view",
        "app.analytics_core.calculators.sales",
        sales_calc.average_order_value_minor,
        unit="INR_minor",
    ),
    # Customers — GROWTH_AND_INTELLIGENCE.md section 13.7.
    _m(
        "customers_total",
        "Total customers",
        "Point-in-time count of non-deleted customers as of the window's end.",
        "customers",
        "count",
        "analytics.customers.view",
        "app.analytics_core.calculators.customers",
        customers_calc.total,
    ),
    _m(
        "customers_new",
        "New customers",
        "Count of non-deleted customers created within the window.",
        "customers",
        "count",
        "analytics.customers.view",
        "app.analytics_core.calculators.customers",
        customers_calc.new,
    ),
    _m(
        "customers_repeat_rate",
        "Repeat customer rate",
        "Percentage of customers with more than one completed order in "
        "the window, among customers with at least one.",
        "customers",
        "percent",
        "analytics.customers.view",
        "app.analytics_core.calculators.customers",
        customers_calc.repeat_rate_pct,
        unit="%",
    ),
    _m(
        "customers_loyalty_enrollment",
        "Loyalty enrollment",
        "Point-in-time count of active loyalty accounts as of the window's end.",
        "customers",
        "count",
        "analytics.customers.view",
        "app.analytics_core.calculators.customers",
        customers_calc.loyalty_enrollment,
    ),
    # Leads — GROWTH_AND_INTELLIGENCE.md section 13.8.
    _m(
        "leads_new",
        "New leads",
        "Count of non-deleted leads created within the window.",
        "leads",
        "count",
        "analytics.leads.view",
        "app.analytics_core.calculators.leads",
        leads_calc.new_leads,
    ),
    _m(
        "leads_open",
        "Open leads",
        "Point-in-time count of non-deleted leads not won/lost/closed, as of the window's end.",
        "leads",
        "count",
        "analytics.leads.view",
        "app.analytics_core.calculators.leads",
        leads_calc.open_leads,
        excluded_states="won, lost, closed",
    ),
    _m(
        "leads_conversion_rate",
        "Lead conversion rate",
        "Percentage of leads created in the window that reached status = "
        "won within the same window.",
        "leads",
        "percent",
        "analytics.leads.view",
        "app.analytics_core.calculators.leads",
        leads_calc.conversion_rate_pct,
        unit="%",
    ),
    # Reservations — GROWTH_AND_INTELLIGENCE.md section 13.9.
    _m(
        "reservations_requests",
        "Reservation requests",
        "Count of reservations created within the window.",
        "reservations",
        "count",
        "analytics.reservations.view",
        "app.analytics_core.calculators.reservations",
        reservations_calc.requests,
    ),
    _m(
        "reservations_confirmed",
        "Confirmed reservations",
        "Count of reservations created within the window with status = confirmed.",
        "reservations",
        "count",
        "analytics.reservations.view",
        "app.analytics_core.calculators.reservations",
        reservations_calc.confirmed,
    ),
    _m(
        "reservations_no_show_rate",
        "No-show rate",
        "No-shows as a share of reservations reaching a seated-or-later "
        "outcome (arrived, seated, completed, no_show) within the window.",
        "reservations",
        "percent",
        "analytics.reservations.view",
        "app.analytics_core.calculators.reservations",
        reservations_calc.no_show_rate_pct,
        unit="%",
    ),
    _m(
        "reservations_average_party_size",
        "Average party size",
        "Average party_size for reservations created within the window.",
        "reservations",
        "decimal",
        "analytics.reservations.view",
        "app.analytics_core.calculators.reservations",
        reservations_calc.average_party_size,
        unit="guests",
    ),
    # Inventory — GROWTH_AND_INTELLIGENCE.md section 13.11.
    _m(
        "inventory_low_stock_items",
        "Low-stock items",
        "Point-in-time count of active inventory items with derived "
        "stock_status = low_stock, as of the window's end.",
        "inventory_suppliers",
        "count",
        "analytics.inventory.view",
        "app.analytics_core.calculators.inventory",
        inventory_calc.low_stock_items,
    ),
    _m(
        "inventory_critical_stock_items",
        "Critical-stock items",
        "Point-in-time count of active inventory items with derived "
        "stock_status = critical_stock, as of the window's end.",
        "inventory_suppliers",
        "count",
        "analytics.inventory.view",
        "app.analytics_core.calculators.inventory",
        inventory_calc.critical_stock_items,
    ),
    _m(
        "inventory_waste_value",
        "Waste value",
        "Wastage quantity valued at each item's average (or standard) "
        "unit cost, for wastage recorded within the window.",
        "inventory_suppliers",
        "currency_minor",
        "analytics.inventory.view",
        "app.analytics_core.calculators.inventory",
        inventory_calc.waste_value_minor,
        unit="INR_minor",
    ),
    # Marketing and loyalty — GROWTH_AND_INTELLIGENCE.md sections 13.12-13.13.
    _m(
        "marketing_active_campaigns",
        "Active campaigns",
        "Point-in-time count of campaigns with status running or "
        "scheduled, as of the window's end.",
        "marketing",
        "count",
        "analytics.marketing_loyalty.view",
        "app.analytics_core.calculators.marketing",
        marketing_calc.active_campaigns,
    ),
    _m(
        "marketing_delivered_messages",
        "Delivered campaign messages",
        "Count of campaign recipients with a delivered_at timestamp within the window.",
        "marketing",
        "count",
        "analytics.marketing_loyalty.view",
        "app.analytics_core.calculators.marketing",
        marketing_calc.delivered_messages,
    ),
    _m(
        "loyalty_members",
        "Loyalty members",
        "Point-in-time count of active loyalty accounts as of the window's end.",
        "loyalty",
        "count",
        "analytics.marketing_loyalty.view",
        "app.analytics_core.calculators.marketing",
        marketing_calc.loyalty_members,
    ),
    _m(
        "loyalty_points_redeemed",
        "Loyalty points redeemed",
        "Sum of redeemed loyalty points (redeem_order, redeem_reward "
        "ledger entries) within the window.",
        "loyalty",
        "count",
        "analytics.marketing_loyalty.view",
        "app.analytics_core.calculators.marketing",
        marketing_calc.loyalty_points_redeemed,
        unit="points",
    ),
    # Feedback and complaints — GROWTH_AND_INTELLIGENCE.md section 13.14.
    _m(
        "feedback_average_rating",
        "Average feedback rating",
        "Average rating (1-5) across feedback entries created within the window.",
        "feedback",
        "decimal",
        "analytics.feedback_complaints.view",
        "app.analytics_core.calculators.feedback",
        feedback_calc.average_rating,
        unit="stars",
    ),
    _m(
        "feedback_response_rate",
        "Feedback response rate",
        "Completed review requests as a share of review requests that "
        "reached the customer, within the window.",
        "feedback",
        "percent",
        "analytics.feedback_complaints.view",
        "app.analytics_core.calculators.feedback",
        feedback_calc.response_rate_pct,
        unit="%",
    ),
    _m(
        "complaints_rate",
        "Complaint rate",
        "Complaints created within the window as a share of completed orders in the same window.",
        "complaints",
        "percent",
        "analytics.feedback_complaints.view",
        "app.analytics_core.calculators.feedback",
        feedback_calc.complaints_rate_pct,
        unit="%",
    ),
    _m(
        "complaints_average_resolution_minutes",
        "Average complaint resolution time",
        "Average minutes between complaint creation and resolution, for "
        "complaints resolved within the window.",
        "complaints",
        "duration_minutes",
        "analytics.feedback_complaints.view",
        "app.analytics_core.calculators.feedback",
        feedback_calc.average_resolution_minutes,
        unit="minutes",
    ),
    # Staff and tasks — GROWTH_AND_INTELLIGENCE.md section 13.2.
    _m(
        "staff_active_count",
        "Active staff",
        "Point-in-time count of active staff user accounts.",
        "staff_tasks",
        "count",
        "analytics.staff.view",
        "app.analytics_core.calculators.staff",
        staff_calc.active_count,
    ),
    _m(
        "staff_overdue_tasks",
        "Overdue tasks",
        "Point-in-time count of open/in-progress/blocked tasks past "
        "their due date, as of the window's end.",
        "staff_tasks",
        "count",
        "analytics.staff.view",
        "app.analytics_core.calculators.staff",
        staff_calc.overdue_tasks,
    ),
    _m(
        "staff_attendance_rate",
        "Attendance rate",
        "Present-or-late attendance records as a share of all recorded "
        "attendance (excluding scheduled days off) within the window.",
        "staff_tasks",
        "percent",
        "analytics.staff.view",
        "app.analytics_core.calculators.staff",
        staff_calc.attendance_rate_pct,
        unit="%",
    ),
)

_METRICS_BY_CODE: dict[str, MetricDef] = {metric.code: metric for metric in METRICS}

if len(_METRICS_BY_CODE) != len(METRICS):
    raise RuntimeError("Duplicate metric code detected in the canonical metric registry.")


def get_metric(code: str) -> MetricDef:
    try:
        return _METRICS_BY_CODE[code]
    except KeyError as exc:
        raise KeyError(f"Unknown metric code: {code!r}") from exc


def metrics_for_domain(domain: str) -> tuple[MetricDef, ...]:
    return tuple(metric for metric in METRICS if metric.domain == domain)


METRIC_CODES: frozenset[str] = frozenset(_METRICS_BY_CODE)
