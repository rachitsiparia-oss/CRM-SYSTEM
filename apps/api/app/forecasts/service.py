"""Forecast definition CRUD and deterministic forecast generation —
GROWTH_AND_INTELLIGENCE.md section 15. `run_forecast` is the directly-
callable engine entry point (manual trigger today; Phase 15 may put it on
a timer). A forecast with insufficient history returns
`status="insufficient_data"` and null `forecast_values` rather than a
fabricated number (section 15.6)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import DEFAULT_PAGE_SIZE
from app.db.models import ForecastDefinition, ForecastSnapshot, StaffUser
from app.forecasts.data import get_daily_history, is_valid_target_metric
from app.forecasts.errors import ForecastError
from app.forecasts.methods import METHODS, backtest_errors


async def create_forecast_definition(
    session: AsyncSession, *, actor: StaffUser, payload: object
) -> ForecastDefinition:
    from app.forecasts.schemas import ForecastDefinitionCreateIn

    assert isinstance(payload, ForecastDefinitionCreateIn)
    if not is_valid_target_metric(payload.target_metric_code):
        raise ForecastError(f"Unknown target metric code: {payload.target_metric_code!r}")
    definition = ForecastDefinition(
        code=payload.code,
        name=payload.name,
        forecast_area=payload.forecast_area,
        method=payload.method,
        method_params=payload.method_params,
        target_metric_code=payload.target_metric_code,
        dimension_filter=payload.dimension_filter,
        minimum_history_periods=payload.minimum_history_periods,
        horizon_periods=payload.horizon_periods,
        is_active=payload.is_active,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(definition)
    await session.flush()
    return definition


async def get_forecast_definition(
    session: AsyncSession, definition_id: uuid.UUID
) -> ForecastDefinition | None:
    return await session.get(ForecastDefinition, definition_id)


async def list_forecast_definitions(
    session: AsyncSession, *, is_active: bool | None = None
) -> list[ForecastDefinition]:
    conditions = []
    if is_active is not None:
        conditions.append(ForecastDefinition.is_active == is_active)
    rows = await session.scalars(
        select(ForecastDefinition).where(*conditions).order_by(ForecastDefinition.name)
    )
    return list(rows.all())


async def run_forecast(session: AsyncSession, definition: ForecastDefinition) -> ForecastSnapshot:
    now = datetime.now(UTC)
    history_span = max(definition.minimum_history_periods, 14)
    history = await get_daily_history(session, definition.target_metric_code, num_days=history_span)
    non_zero_count = sum(1 for v in history if v != 0)
    horizon_start = now
    horizon_end = now + timedelta(days=definition.horizon_periods)
    historical_window_start = now - timedelta(days=history_span)

    if non_zero_count < definition.minimum_history_periods:
        snapshot = ForecastSnapshot(
            forecast_definition_id=definition.id,
            historical_window_start=historical_window_start,
            historical_window_end=now,
            horizon_start=horizon_start,
            horizon_end=horizon_end,
            status="insufficient_data",
            input_data_completeness_pct=((non_zero_count / len(history)) * 100 if history else 0),
            forecast_values=None,
            method_version=f"{definition.method}:v1",
            failure_details=(
                f"Only {non_zero_count} non-zero historical periods available; "
                f"{definition.minimum_history_periods} required."
            ),
        )
        session.add(snapshot)
        await session.flush()
        return snapshot

    forecast_fn = METHODS[definition.method]
    method_params = definition.method_params or {}
    predicted = forecast_fn(history, horizon=definition.horizon_periods, **method_params)
    mae, mape = backtest_errors(history, method=definition.method)

    forecast_values = [
        {
            "period_offset": index,
            "date": (now + timedelta(days=index + 1)).date().isoformat(),
            "value": str(value),
        }
        for index, value in enumerate(predicted)
    ]

    snapshot = ForecastSnapshot(
        forecast_definition_id=definition.id,
        historical_window_start=historical_window_start,
        historical_window_end=now,
        horizon_start=horizon_start,
        horizon_end=horizon_end,
        status="ok",
        input_data_completeness_pct=(non_zero_count / len(history)) * 100 if history else 0,
        forecast_values=forecast_values,
        confidence_interval=None,
        assumptions=(
            f"Method: {definition.method}. Statistical baseline only — no holiday, "
            "campaign, menu, or closure effects are modeled unless represented in the "
            "underlying transactional data itself."
        ),
        backtest_mae=mae,
        backtest_mape=mape,
        method_version=f"{definition.method}:v1",
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def get_forecast_snapshot(
    session: AsyncSession, snapshot_id: uuid.UUID
) -> ForecastSnapshot | None:
    return await session.get(ForecastSnapshot, snapshot_id)


async def list_forecast_snapshots(
    session: AsyncSession,
    *,
    forecast_definition_id: uuid.UUID,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[ForecastSnapshot], int]:
    conditions = (ForecastSnapshot.forecast_definition_id == forecast_definition_id,)
    total = (
        await session.scalar(select(func.count()).select_from(ForecastSnapshot).where(*conditions))
    ) or 0
    rows = await session.scalars(
        select(ForecastSnapshot)
        .where(*conditions)
        .order_by(ForecastSnapshot.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.all()), total
