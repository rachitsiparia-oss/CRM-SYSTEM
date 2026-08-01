from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ForecastArea = Literal["order_volume", "net_revenue", "reservation_covers", "inventory_consumption"]
ForecastMethod = Literal[
    "moving_average", "linear_trend", "seasonal_naive", "exponential_smoothing"
]
ForecastSnapshotStatus = Literal["ok", "insufficient_data", "failed"]


class ForecastDefinitionCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    forecast_area: ForecastArea
    method: ForecastMethod
    method_params: dict[str, object] | None = None
    target_metric_code: str
    dimension_filter: dict[str, object] | None = None
    minimum_history_periods: int = Field(default=14, ge=1)
    horizon_periods: int = Field(default=7, ge=1, le=90)
    is_active: bool = True


class ForecastDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    forecast_area: ForecastArea
    method: ForecastMethod
    method_params: dict[str, object] | None
    target_metric_code: str
    dimension_filter: dict[str, object] | None
    minimum_history_periods: int
    horizon_periods: int
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ForecastSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    forecast_definition_id: uuid.UUID
    historical_window_start: datetime
    historical_window_end: datetime
    horizon_start: datetime
    horizon_end: datetime
    status: ForecastSnapshotStatus
    input_data_completeness_pct: Decimal | None
    forecast_values: list[dict[str, object]] | None
    confidence_interval: dict[str, object] | None
    assumptions: str | None
    backtest_mae: Decimal | None
    backtest_mape: Decimal | None
    method_version: str
    failure_details: str | None
    created_at: datetime
