import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    AppendOnlyTimestampMixin,
    AuditedMixin,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

# GROWTH_AND_INTELLIGENCE.md section 15.2 (approved subset actually built in
# Phase 14, per PROJECT_PLAN.md's "initial forecastable metrics" list).
FORECAST_AREAS = ("order_volume", "net_revenue", "reservation_covers", "inventory_consumption")
# GROWTH_AND_INTELLIGENCE.md section 15.5 "baseline before complexity" —
# transparent statistical methods only, no invented/black-box model names.
FORECAST_METHODS = ("moving_average", "linear_trend", "seasonal_naive", "exponential_smoothing")
FORECAST_SNAPSHOT_STATUSES = ("ok", "insufficient_data", "failed")


class ForecastDefinition(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A configured, reusable forecast (area + method + target metric).
    `dimension_filter` narrows the target metric to a specific dimension
    value (e.g. a single `inventory_item_id` for ingredient-demand
    forecasts) using the same allowlisted filter shape
    `app.analytics_core` uses elsewhere — never a raw column/table
    reference."""

    __tablename__ = "forecast_definitions"
    __table_args__ = (
        CheckConstraint(f"forecast_area IN {FORECAST_AREAS!r}", name="valid_forecast_area"),
        CheckConstraint(f"method IN {FORECAST_METHODS!r}", name="valid_method"),
        CheckConstraint("minimum_history_periods >= 1", name="valid_minimum_history_periods"),
        CheckConstraint("horizon_periods >= 1", name="valid_horizon_periods"),
        Index("uq_forecast_definitions_code", "code", unique=True),
        Index("ix_forecast_definitions_forecast_area", "forecast_area"),
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    forecast_area: Mapped[str] = mapped_column(String(32), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    method_params: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    target_metric_code: Mapped[str] = mapped_column(String(80), nullable=False)
    dimension_filter: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    minimum_history_periods: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    horizon_periods: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class ForecastSnapshot(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """One immutable forecast generation — GROWTH_AND_INTELLIGENCE.md
    section 15.3/15.6. `created_at` (from `AppendOnlyTimestampMixin`) *is*
    the "generated time" field the spec calls for; no separate column is
    needed. `status="insufficient_data"` with null `forecast_values` is
    the required outcome when history is too short, rather than a
    fabricated number (section 15.6)."""

    __tablename__ = "forecast_snapshots"
    __table_args__ = (
        CheckConstraint(f"status IN {FORECAST_SNAPSHOT_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "historical_window_end >= historical_window_start", name="valid_historical_window_range"
        ),
        CheckConstraint("horizon_end >= horizon_start", name="valid_horizon_range"),
        CheckConstraint(
            "input_data_completeness_pct IS NULL OR input_data_completeness_pct BETWEEN 0 AND 100",
            name="valid_completeness_pct",
        ),
        Index("ix_forecast_snapshots_forecast_definition_id", "forecast_definition_id"),
        Index("ix_forecast_snapshots_status", "status"),
    )

    forecast_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("forecast_definitions.id"), nullable=False
    )
    historical_window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    historical_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    input_data_completeness_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    forecast_values: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB, nullable=True)
    confidence_interval: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    assumptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    backtest_mae: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    backtest_mape: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    method_version: Mapped[str] = mapped_column(String(120), nullable=False)
    failure_details: Mapped[str | None] = mapped_column(Text, nullable=True)
