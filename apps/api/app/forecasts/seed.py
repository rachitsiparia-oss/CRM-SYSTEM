"""Idempotent development seed data — one forecast definition per approved
forecast area (GROWTH_AND_INTELLIGENCE.md section 15.2's "initial
forecastable metrics" subset this phase implements)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ForecastDefinition, StaffUser

_DEFINITIONS = (
    {
        "code": "order-volume-daily",
        "name": "Daily order volume",
        "forecast_area": "order_volume",
        "method": "moving_average",
        "target_metric_code": "sales_completed_order_count",
    },
    {
        "code": "net-revenue-daily",
        "name": "Daily net revenue",
        "forecast_area": "net_revenue",
        "method": "linear_trend",
        "target_metric_code": "exec_net_sales",
    },
    {
        "code": "reservation-covers-daily",
        "name": "Daily reservation covers",
        "forecast_area": "reservation_covers",
        "method": "seasonal_naive",
        "target_metric_code": "reservation_covers_total",
    },
    {
        "code": "inventory-consumption-daily",
        "name": "Daily inventory consumption",
        "forecast_area": "inventory_consumption",
        "method": "exponential_smoothing",
        "target_metric_code": "inventory_consumption_total",
    },
)


async def seed_forecast_definitions(session: AsyncSession) -> None:
    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    if actor is None:
        return

    for entry in _DEFINITIONS:
        existing = await session.scalar(
            select(ForecastDefinition).where(ForecastDefinition.code == entry["code"])
        )
        if existing is not None:
            continue
        session.add(
            ForecastDefinition(
                code=entry["code"],
                name=entry["name"],
                forecast_area=entry["forecast_area"],
                method=entry["method"],
                target_metric_code=entry["target_metric_code"],
                minimum_history_periods=14,
                horizon_periods=7,
                is_active=True,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
    await session.flush()
