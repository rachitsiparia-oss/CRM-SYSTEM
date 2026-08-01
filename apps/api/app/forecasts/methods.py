"""Transparent statistical forecasting methods — GROWTH_AND_INTELLIGENCE.md
section 15.5's "baseline before complexity": explainable statistical
baselines only, no black-box or invented model names. Every function is a
pure `list[Decimal] -> list[Decimal]` transform with no hidden state, so a
forecast is fully reproducible from its stored `method` + `method_params`.
"""

from decimal import Decimal

DEFAULT_SEASON_LENGTH = 7
DEFAULT_SMOOTHING_ALPHA = Decimal("0.3")


def moving_average(history: list[Decimal], *, horizon: int, window: int = 7) -> list[Decimal]:
    span = history[-window:] if len(history) >= window else history
    average = sum(span) / Decimal(len(span)) if span else Decimal(0)
    return [average] * horizon


def linear_trend(history: list[Decimal], *, horizon: int) -> list[Decimal]:
    n = len(history)
    if n < 2:
        return [history[-1] if history else Decimal(0)] * horizon
    xs = list(range(n))
    mean_x = Decimal(sum(xs)) / Decimal(n)
    mean_y = sum(history) / Decimal(n)
    numerator = sum((Decimal(x) - mean_x) * (y - mean_y) for x, y in zip(xs, history, strict=True))
    denominator = sum((Decimal(x) - mean_x) ** 2 for x in xs)
    slope = numerator / denominator if denominator != 0 else Decimal(0)
    intercept = mean_y - slope * mean_x
    return [intercept + slope * Decimal(n - 1 + step) for step in range(1, horizon + 1)]


def seasonal_naive(
    history: list[Decimal], *, horizon: int, season_length: int = DEFAULT_SEASON_LENGTH
) -> list[Decimal]:
    if not history:
        return [Decimal(0)] * horizon
    effective_season = min(season_length, len(history))
    return [history[-effective_season + (step % effective_season)] for step in range(horizon)]


def exponential_smoothing(
    history: list[Decimal], *, horizon: int, alpha: Decimal = DEFAULT_SMOOTHING_ALPHA
) -> list[Decimal]:
    if not history:
        return [Decimal(0)] * horizon
    level = history[0]
    for value in history[1:]:
        level = alpha * value + (Decimal(1) - alpha) * level
    # Level-only (no trend/seasonality) smoothing: the forecast is flat at
    # the final smoothed level for every horizon step — a documented
    # limitation surfaced in `ForecastSnapshot.assumptions`, not hidden.
    return [level] * horizon


METHODS = {
    "moving_average": moving_average,
    "linear_trend": linear_trend,
    "seasonal_naive": seasonal_naive,
    "exponential_smoothing": exponential_smoothing,
}


def backtest_errors(
    history: list[Decimal], *, method: str, holdout: int = 7
) -> tuple[Decimal | None, Decimal | None]:
    """Mean absolute error and mean absolute percentage error from a
    simple holdout backtest: forecast the last `holdout` known points using
    only the points before them, then compare — GROWTH_AND_INTELLIGENCE.md
    section 15.6's "track ... absolute error, percentage error"."""
    if len(history) <= holdout:
        return None, None
    train, actual = history[:-holdout], history[-holdout:]
    forecast_fn = METHODS[method]
    predicted = forecast_fn(train, horizon=holdout)
    errors = [abs(a - p) for a, p in zip(actual, predicted, strict=True)]
    mae = sum(errors) / Decimal(len(errors))
    non_zero_pairs = [(a, e) for a, e in zip(actual, errors, strict=True) if a != 0]
    mape = (
        (sum(e / abs(a) for a, e in non_zero_pairs) / Decimal(len(non_zero_pairs))) * Decimal(100)
        if non_zero_pairs
        else None
    )
    return mae, mape
