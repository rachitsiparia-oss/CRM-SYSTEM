"""Report-window resolution — GROWTH_AND_INTELLIGENCE.md section 13.3
(supported windows) and the Phase 14 instruction's requirement for
business-timezone-consistent time handling with equivalent-length prior-
period comparisons. All boundaries are computed in the restaurant's
configured timezone (CLAUDE.md section 7), then converted to UTC for
querying — the same pattern `app.orders.service.get_dashboard_stats` and
`app.inventory.dashboard.get_dashboard_stats` already established.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

RESTAURANT_TIMEZONE = ZoneInfo("Asia/Kolkata")

REPORT_WINDOW_CODES = (
    "today",
    "yesterday",
    "current_week",
    "previous_week",
    "current_month",
    "previous_month",
    "current_quarter",
    "previous_quarter",
    "custom",
)

# GROWTH_AND_INTELLIGENCE.md section 13.20 "custom date range too large" —
# bounded so a report/export can never scan an unbounded history.
MAX_CUSTOM_RANGE_DAYS = 366


class InvalidWindowError(ValueError):
    """Raised for an unknown window code or an invalid/oversized custom range."""


@dataclass(frozen=True)
class ResolvedWindow:
    window_code: str
    start: datetime
    end: datetime
    comparison_start: datetime | None
    comparison_end: datetime | None
    timezone: str = "Asia/Kolkata"


def _local_midnight(moment: datetime) -> datetime:
    return moment.astimezone(RESTAURANT_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)


def _quarter_start(local_midnight: datetime) -> datetime:
    quarter_start_month = ((local_midnight.month - 1) // 3) * 3 + 1
    return local_midnight.replace(month=quarter_start_month, day=1)


def _add_months(moment: datetime, months: int) -> datetime:
    total = moment.month - 1 + months
    year = moment.year + total // 12
    month = total % 12 + 1
    return moment.replace(year=year, month=month, day=1)


def resolve_window(
    window_code: str,
    *,
    now: datetime | None = None,
    custom_start: datetime | None = None,
    custom_end: datetime | None = None,
) -> ResolvedWindow:
    """Returns UTC-normalized `[start, end)` boundaries plus an
    equivalent-length prior-period comparison window, per
    GROWTH_AND_INTELLIGENCE.md section 13.3's "comparisons must clearly
    state the comparison period."
    """
    if window_code not in REPORT_WINDOW_CODES:
        raise InvalidWindowError(f"Unknown report window: {window_code!r}")

    reference = (now or datetime.now(UTC)).astimezone(UTC)
    today_local = _local_midnight(reference)

    if window_code == "today":
        start_local, end_local = today_local, today_local + timedelta(days=1)
        comparison_start_local = start_local - timedelta(days=1)
        comparison_end_local = start_local
    elif window_code == "yesterday":
        end_local = today_local
        start_local = end_local - timedelta(days=1)
        comparison_start_local = start_local - timedelta(days=1)
        comparison_end_local = start_local
    elif window_code == "current_week":
        start_local = today_local - timedelta(days=today_local.weekday())
        end_local = start_local + timedelta(days=7)
        comparison_start_local = start_local - timedelta(days=7)
        comparison_end_local = start_local
    elif window_code == "previous_week":
        this_week_start = today_local - timedelta(days=today_local.weekday())
        start_local = this_week_start - timedelta(days=7)
        end_local = this_week_start
        comparison_start_local = start_local - timedelta(days=7)
        comparison_end_local = start_local
    elif window_code == "current_month":
        start_local = today_local.replace(day=1)
        end_local = _add_months(start_local, 1)
        prior_start = _add_months(start_local, -1)
        comparison_start_local, comparison_end_local = prior_start, start_local
    elif window_code == "previous_month":
        this_month_start = today_local.replace(day=1)
        start_local = _add_months(this_month_start, -1)
        end_local = this_month_start
        comparison_start_local = _add_months(start_local, -1)
        comparison_end_local = start_local
    elif window_code == "current_quarter":
        start_local = _quarter_start(today_local)
        end_local = _add_months(start_local, 3)
        comparison_start_local = _add_months(start_local, -3)
        comparison_end_local = start_local
    elif window_code == "previous_quarter":
        this_quarter_start = _quarter_start(today_local)
        start_local = _add_months(this_quarter_start, -3)
        end_local = this_quarter_start
        comparison_start_local = _add_months(start_local, -3)
        comparison_end_local = start_local
    else:  # "custom"
        if custom_start is None or custom_end is None:
            raise InvalidWindowError("A custom window requires both custom_start and custom_end.")
        start_local = _local_midnight(custom_start.astimezone(UTC))
        end_local = _local_midnight(custom_end.astimezone(UTC)) + timedelta(days=1)
        if end_local <= start_local:
            raise InvalidWindowError("custom_end must be after custom_start.")
        span_days = (end_local - start_local).days
        if span_days > MAX_CUSTOM_RANGE_DAYS:
            raise InvalidWindowError(
                f"Custom range spans {span_days} days, exceeding the "
                f"{MAX_CUSTOM_RANGE_DAYS}-day maximum."
            )
        comparison_start_local = start_local - (end_local - start_local)
        comparison_end_local = start_local

    return ResolvedWindow(
        window_code=window_code,
        start=start_local.astimezone(UTC),
        end=end_local.astimezone(UTC),
        comparison_start=comparison_start_local.astimezone(UTC),
        comparison_end=comparison_end_local.astimezone(UTC),
    )
