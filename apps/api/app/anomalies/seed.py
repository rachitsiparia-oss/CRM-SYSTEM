"""Idempotent development seed data — anomaly rules over metrics this
phase's registry actually implements (GROWTH_AND_INTELLIGENCE.md section
15.7's example list, scoped to the built metric set)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnomalyRule, StaffUser

_RULES = (
    {
        "code": "unusual-revenue-decline",
        "name": "Unusual revenue decline",
        "metric_code": "exec_net_sales",
        "rule_type": "pct_change_prior_period",
        "threshold_value": 20,
        "severity": "high",
    },
    {
        "code": "elevated-cancellation-rate",
        "name": "Elevated order cancellation rate",
        "metric_code": "sales_cancelled_order_count",
        "rule_type": "rolling_average_deviation",
        "threshold_value": 50,
        "rolling_window_periods": 7,
        "minimum_sample_size": 3,
        "severity": "medium",
    },
    {
        "code": "low-stock-exposure",
        "name": "Low-stock exposure",
        "metric_code": "inventory_critical_stock_items",
        "rule_type": "absolute_threshold",
        "comparison_operator": "gt",
        "threshold_value": 5,
        "severity": "high",
    },
    {
        "code": "reservation-no-show-spike",
        "name": "Reservation no-show spike",
        "metric_code": "reservations_no_show_rate",
        "rule_type": "pct_change_prior_period",
        "threshold_value": 50,
        "severity": "medium",
    },
    {
        "code": "elevated-complaint-rate",
        "name": "Elevated complaint rate",
        "metric_code": "complaints_rate",
        "rule_type": "rolling_average_deviation",
        "threshold_value": 40,
        "rolling_window_periods": 7,
        "minimum_sample_size": 3,
        "severity": "high",
    },
)


async def seed_anomaly_rules(session: AsyncSession) -> None:
    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    if actor is None:
        return

    for entry in _RULES:
        existing = await session.scalar(
            select(AnomalyRule).where(AnomalyRule.code == entry["code"])
        )
        if existing is not None:
            continue
        session.add(
            AnomalyRule(
                code=entry["code"],
                name=entry["name"],
                metric_code=entry["metric_code"],
                rule_type=entry["rule_type"],
                comparison_operator=entry.get("comparison_operator"),
                threshold_value=entry["threshold_value"],
                rolling_window_periods=entry.get("rolling_window_periods"),
                minimum_sample_size=entry.get("minimum_sample_size", 1),
                cooldown_hours=24,
                severity=entry["severity"],
                is_active=True,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
    await session.flush()
