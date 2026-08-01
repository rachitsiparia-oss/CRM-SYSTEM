"""Tests for `app.forecasts` — the transparent statistical methods (pure
functions, no DB) and `run_forecast`'s insufficient-data path."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from decimal import Decimal

from app.db.models import ForecastDefinition, StaffUser
from app.forecasts.methods import (
    backtest_errors,
    exponential_smoothing,
    linear_trend,
    moving_average,
    seasonal_naive,
)
from app.forecasts.service import run_forecast
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _decimals(values: list[int]) -> list[Decimal]:
    return [Decimal(v) for v in values]


def test_moving_average_uses_recent_window_mean() -> None:
    history = _decimals([10, 10, 10, 20, 20, 20, 30])
    forecast = moving_average(history, horizon=3, window=3)
    assert forecast == [Decimal(70) / Decimal(3)] * 3


def test_linear_trend_extrapolates_constant_slope() -> None:
    history = _decimals([1, 2, 3, 4, 5])
    forecast = linear_trend(history, horizon=2)
    assert forecast[0] == Decimal(6)
    assert forecast[1] == Decimal(7)


def test_linear_trend_flat_history_has_zero_slope() -> None:
    history = _decimals([5, 5, 5, 5])
    forecast = linear_trend(history, horizon=2)
    assert forecast == [Decimal(5), Decimal(5)]


def test_seasonal_naive_repeats_prior_season() -> None:
    history = _decimals([1, 2, 3, 4, 5, 6, 7])
    forecast = seasonal_naive(history, horizon=7, season_length=7)
    assert forecast == history


def test_exponential_smoothing_is_flat_across_horizon() -> None:
    history = _decimals([10, 20, 10, 20])
    forecast = exponential_smoothing(history, horizon=3)
    assert len(forecast) == 3
    assert forecast[0] == forecast[1] == forecast[2]


def test_backtest_errors_returns_none_for_short_history() -> None:
    mae, mape = backtest_errors(_decimals([1, 2, 3]), method="moving_average", holdout=7)
    assert mae is None
    assert mape is None


def test_backtest_errors_computes_mae_for_perfect_flat_series() -> None:
    history = _decimals([10] * 20)
    mae, mape = backtest_errors(history, method="moving_average", holdout=5)
    assert mae == Decimal(0)
    assert mape == Decimal(0)


async def test_run_forecast_reports_insufficient_data_for_new_definition(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    definition = ForecastDefinition(
        id=uuid.uuid4(),
        code=f"test-forecast-{uuid.uuid4().hex[:8]}",
        name="Test forecast",
        forecast_area="order_volume",
        method="moving_average",
        target_metric_code="sales_completed_order_count",
        minimum_history_periods=60,  # deliberately high — no seed data spans 60 days
        horizon_periods=7,
        is_active=True,
        created_by=actor.id,
        updated_by=actor.id,
    )
    db_session.add(definition)
    await db_session.flush()

    snapshot = await run_forecast(db_session, definition)
    assert snapshot.status == "insufficient_data"
    assert snapshot.forecast_values is None
    assert snapshot.failure_details is not None
