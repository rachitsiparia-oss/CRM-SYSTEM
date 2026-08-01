"""The safe query engine — the only path `app.reports`, `app.anomalies`,
`app.forecasts`, and `app.controlled_ai` use to read a metric value.
Clients (including the report builder) may only ever supply a
`metric_code` (validated against `app.analytics_core.registry.METRICS`)
plus a bounded window; there is no raw SQL, table name, or column name
accepted from any caller.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.registry import METRICS, MetricDef, MetricValue, get_metric
from app.analytics_core.windows import ResolvedWindow, resolve_window


def has_permission(permissions: frozenset[str], permission_code: str) -> bool:
    """A synchronous, in-memory membership check against an already-
    resolved effective-permission set — distinct from
    `app.permissions.service.has_permission` (which queries the database
    for a single staff user). Callers here fetch the caller's effective
    permission set once per request via
    `app.permissions.service.get_effective_permissions` and reuse it
    across every metric in a dashboard/report, which may reference dozens
    of metric codes in one request."""
    return permission_code in permissions


class MetricPermissionDeniedError(Exception):
    def __init__(self, metric_code: str, required_permission: str) -> None:
        self.metric_code = metric_code
        self.required_permission = required_permission
        super().__init__(
            f"Missing {required_permission!r} required to read metric {metric_code!r}."
        )


@dataclass(frozen=True)
class MetricResult:
    metric: MetricDef
    window: ResolvedWindow
    value: MetricValue
    comparison_value: MetricValue | None
    change_pct: Decimal | None
    generated_at: datetime


def _pct_change(current: MetricValue, previous: MetricValue | None) -> Decimal | None:
    if previous is None:
        return None
    previous_decimal = Decimal(previous)
    if previous_decimal == 0:
        # GROWTH_AND_INTELLIGENCE.md section 13.20/13.21: "denominator is
        # zero" / "zero denominators do not produce misleading
        # percentages" — return None (no change figure), never divide by
        # zero or fabricate 0%/100%.
        return None
    return ((Decimal(current) - previous_decimal) / previous_decimal) * Decimal(100)


async def check_metric_permission(metric_code: str, permissions: frozenset[str]) -> MetricDef:
    metric = get_metric(metric_code)
    if not has_permission(permissions, metric.required_permission):
        raise MetricPermissionDeniedError(metric_code, metric.required_permission)
    return metric


async def run_metric_query(
    session: AsyncSession,
    *,
    metric_code: str,
    permissions: frozenset[str],
    window_code: str,
    custom_start: datetime | None = None,
    custom_end: datetime | None = None,
    include_comparison: bool = True,
) -> MetricResult:
    metric = await check_metric_permission(metric_code, permissions)
    window = resolve_window(window_code, custom_start=custom_start, custom_end=custom_end)

    value = await metric.calculator(session, window)

    comparison_value: MetricValue | None = None
    if include_comparison and metric.supports_comparison and window.comparison_start is not None:
        comparison_window = ResolvedWindow(
            window_code=window.window_code,
            start=window.comparison_start,
            end=window.comparison_end,  # type: ignore[arg-type]
            comparison_start=None,
            comparison_end=None,
            timezone=window.timezone,
        )
        comparison_value = await metric.calculator(session, comparison_window)

    return MetricResult(
        metric=metric,
        window=window,
        value=value,
        comparison_value=comparison_value,
        change_pct=_pct_change(value, comparison_value),
        generated_at=datetime.now(UTC),
    )


def require_metric_permission_or_404(metric_code: str, permissions: frozenset[str]) -> MetricDef:
    """Synchronous helper for router-layer validation before a query
    executes — 404s an unknown code (never leaks "code exists but denied"
    vs "code doesn't exist" distinctly, matching CLAUDE.md's "do not reveal
    ... through inconsistent ... error messages" principle applied to
    metric enumeration)."""
    try:
        metric = get_metric(metric_code)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown metric code."
        ) from exc
    if not has_permission(permissions, metric.required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission to view this metric: {metric.required_permission}.",
        )
    return metric


def all_metrics() -> tuple[MetricDef, ...]:
    return METRICS
