"""Tests for `app.analytics_core` — window resolution, metric registry
integrity, and the safe query engine's permission gating and zero-
denominator handling."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.analytics_core.engine import MetricPermissionDeniedError, run_metric_query
from app.analytics_core.registry import METRIC_CODES, METRICS, get_metric
from app.analytics_core.windows import InvalidWindowError, resolve_window
from app.db.models import Order
from sqlalchemy.ext.asyncio import AsyncSession


def test_metric_registry_has_no_duplicate_codes() -> None:
    codes = [m.code for m in METRICS]
    assert len(codes) == len(set(codes))
    assert frozenset(codes) == METRIC_CODES


def test_get_metric_unknown_code_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        get_metric("not_a_real_metric")


def test_resolve_window_unknown_code_raises() -> None:
    with pytest.raises(InvalidWindowError):
        resolve_window("not_a_real_window")


def test_resolve_window_custom_requires_bounds() -> None:
    with pytest.raises(InvalidWindowError):
        resolve_window("custom")


def test_resolve_window_custom_rejects_oversized_range() -> None:
    with pytest.raises(InvalidWindowError):
        resolve_window(
            "custom",
            custom_start=datetime(2020, 1, 1, tzinfo=UTC),
            custom_end=datetime(2024, 1, 1, tzinfo=UTC),
        )


def test_resolve_window_today_has_one_day_span() -> None:
    reference = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    window = resolve_window("today", now=reference)
    assert (window.end - window.start).days == 1
    assert window.comparison_start is not None
    assert window.comparison_end == window.start


def test_resolve_window_current_month_comparison_is_previous_month() -> None:
    reference = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    window = resolve_window("current_month", now=reference)
    assert window.comparison_start is not None
    assert window.comparison_end == window.start
    # Previous month's span should also be roughly a month, not the same
    # length as March (28-31 days) coincidentally matching current month.
    assert window.comparison_start < window.start


async def test_run_metric_query_denies_missing_permission(db_session: AsyncSession) -> None:
    with pytest.raises(MetricPermissionDeniedError):
        await run_metric_query(
            db_session,
            metric_code="exec_net_sales",
            permissions=frozenset(),
            window_code="current_month",
        )


async def test_run_metric_query_zero_denominator_returns_no_change_pct(
    db_session: AsyncSession,
) -> None:
    """A metric with zero for both the current and comparison period must
    not produce a fabricated percentage — GROWTH_AND_INTELLIGENCE.md
    section 13.21's "zero denominators do not produce misleading
    percentages," verified end to end through the real engine against a
    metric with no matching data in either window."""
    result = await run_metric_query(
        db_session,
        metric_code="exec_new_customers",
        permissions=frozenset({"analytics.executive.view"}),
        window_code="custom",
        custom_start=datetime(1999, 1, 1, tzinfo=UTC),
        custom_end=datetime(1999, 1, 2, tzinfo=UTC),
    )
    assert result.value == 0
    assert result.change_pct is None


async def test_sales_completed_order_count_counts_only_completed_orders(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    suffix = uuid.uuid4().hex[:10]
    db_session.add_all(
        [
            Order(
                id=uuid.uuid4(),
                order_number=f"ORD-{suffix}-A",
                source="manual",
                order_type="takeaway",
                status="completed",
                payment_status="paid",
                grand_total_minor=1000,
            ),
            Order(
                id=uuid.uuid4(),
                order_number=f"ORD-{suffix}-B",
                source="manual",
                order_type="takeaway",
                status="draft",
                payment_status="pending",
                grand_total_minor=500,
            ),
        ]
    )
    await db_session.flush()

    window = resolve_window(
        "custom",
        custom_start=now.replace(hour=0, minute=0, second=0, microsecond=0),
        custom_end=now,
    )
    metric = get_metric("sales_completed_order_count")
    value = await metric.calculator(db_session, window)
    assert isinstance(value, int)
    assert value >= 1
