"""Deterministic anomaly evaluation — GROWTH_AND_INTELLIGENCE.md section
15.7 and the Phase 14 instruction's six rule styles. `evaluate_all_active_rules`
is the directly-callable, idempotent entry point Phase 15 will register on
a timer (the "engine, not scheduler" split); it is safe to call repeatedly
— `AnomalyFinding.dedup_key` plus each rule's `cooldown_hours` prevent
duplicate or overly-frequent alerts for the same underlying condition.

Rule evaluation reads metrics directly through each metric's calculator
(not through `app.analytics_core.engine.run_metric_query`) because this is
an internal system process with no single acting user to permission-check
against — the same "system engine, no per-call permission gate" shape
`app.complaints.service.run_sla_escalations` already uses; the *trigger*
endpoint is what's permission-gated, not the engine itself.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.registry import get_metric
from app.analytics_core.windows import resolve_window
from app.db.models import AnomalyFinding, AnomalyRule


def _dedup_key(rule: AnomalyRule, observed_date: str) -> str:
    return f"{rule.id}:{observed_date}"


async def _metric_value_for_daily_window(
    session: AsyncSession, metric_code: str, *, days_ago: int
) -> Decimal:
    reference = datetime.now(UTC) - timedelta(days=days_ago)
    window = resolve_window("today", now=reference)
    metric = get_metric(metric_code)
    value = await metric.calculator(session, window)
    return Decimal(value)


async def _existing_finding(session: AsyncSession, dedup_key: str) -> AnomalyFinding | None:
    result: AnomalyFinding | None = await session.scalar(
        select(AnomalyFinding).where(AnomalyFinding.dedup_key == dedup_key)
    )
    return result


async def _within_cooldown(session: AsyncSession, rule: AnomalyRule) -> bool:
    if rule.cooldown_hours <= 0:
        return False
    cutoff = datetime.now(UTC) - timedelta(hours=rule.cooldown_hours)
    recent: AnomalyFinding | None = await session.scalar(
        select(AnomalyFinding)
        .where(AnomalyFinding.anomaly_rule_id == rule.id, AnomalyFinding.created_at >= cutoff)
        .order_by(AnomalyFinding.created_at.desc())
        .limit(1)
    )
    return recent is not None


def _compare(operator: str, observed: Decimal, threshold: Decimal) -> bool:
    if operator == "gt":
        return observed > threshold
    if operator == "gte":
        return observed >= threshold
    if operator == "lt":
        return observed < threshold
    return observed <= threshold  # "lte"


async def evaluate_rule(session: AsyncSession, rule: AnomalyRule) -> AnomalyFinding | None:
    if not rule.is_active:
        return None
    if await _within_cooldown(session, rule):
        return None

    metric = get_metric(rule.metric_code)
    yesterday = datetime.now(UTC) - timedelta(days=1)
    observed_window = resolve_window("today", now=yesterday)
    observed_value = await metric.calculator(session, observed_window)
    observed = Decimal(observed_value)
    dedup_key = _dedup_key(rule, observed_window.start.date().isoformat())

    if await _existing_finding(session, dedup_key) is not None:
        return None

    finding_kwargs: dict[str, object] | None = None

    if rule.rule_type in ("absolute_threshold", "count_rate_threshold"):
        if rule.comparison_operator is None or rule.threshold_value is None:
            return None
        if _compare(rule.comparison_operator, observed, rule.threshold_value):
            finding_kwargs = {
                "expected_value": rule.threshold_value,
                "deviation_pct": None,
                "evidence": {
                    "rule_type": rule.rule_type,
                    "comparison_operator": rule.comparison_operator,
                    "threshold_value": str(rule.threshold_value),
                },
            }

    elif rule.rule_type == "pct_change_prior_period":
        prior = await _metric_value_for_daily_window(session, rule.metric_code, days_ago=2)
        if prior != 0 and rule.threshold_value is not None:
            change_pct = ((observed - prior) / prior) * Decimal(100)
            if abs(change_pct) >= rule.threshold_value:
                finding_kwargs = {
                    "expected_value": prior,
                    "deviation_pct": change_pct,
                    "evidence": {
                        "rule_type": rule.rule_type,
                        "prior_value": str(prior),
                        "change_pct": str(change_pct),
                        "threshold_pct": str(rule.threshold_value),
                    },
                }

    elif rule.rule_type == "rolling_average_deviation":
        window_size = rule.rolling_window_periods or 7
        if window_size < rule.minimum_sample_size:
            return None
        history = [
            await _metric_value_for_daily_window(session, rule.metric_code, days_ago=d)
            for d in range(2, 2 + window_size)
        ]
        non_zero_history = [v for v in history if v != 0]
        if len(non_zero_history) < rule.minimum_sample_size:
            return None
        rolling_average = sum(non_zero_history) / Decimal(len(non_zero_history))
        if rolling_average != 0 and rule.threshold_value is not None:
            deviation_pct = ((observed - rolling_average) / rolling_average) * Decimal(100)
            if abs(deviation_pct) >= rule.threshold_value:
                finding_kwargs = {
                    "expected_value": rolling_average,
                    "deviation_pct": deviation_pct,
                    "evidence": {
                        "rule_type": rule.rule_type,
                        "rolling_average": str(rolling_average),
                        "sample_size": len(non_zero_history),
                        "deviation_pct": str(deviation_pct),
                        "threshold_pct": str(rule.threshold_value),
                    },
                }

    elif rule.rule_type == "consecutive_deterioration":
        run_length = rule.rolling_window_periods or 3
        if run_length < 2:
            return None
        series = [
            await _metric_value_for_daily_window(session, rule.metric_code, days_ago=d)
            for d in range(1, 1 + run_length)
        ]
        series.reverse()  # oldest -> newest, ending at "observed"
        direction = rule.comparison_operator or "gt"
        deteriorating = all(
            _compare(direction, series[i], series[i - 1]) for i in range(1, len(series))
        )
        if deteriorating:
            finding_kwargs = {
                "expected_value": series[0],
                "deviation_pct": None,
                "evidence": {
                    "rule_type": rule.rule_type,
                    "series": [str(v) for v in series],
                    "direction": direction,
                },
            }

    elif rule.rule_type == "missing_activity":
        run_length = rule.rolling_window_periods or 3
        series = [
            await _metric_value_for_daily_window(session, rule.metric_code, days_ago=d)
            for d in range(1, 1 + run_length)
        ]
        if series and all(v == 0 for v in series):
            finding_kwargs = {
                "expected_value": None,
                "deviation_pct": None,
                "evidence": {"rule_type": rule.rule_type, "consecutive_zero_periods": run_length},
            }

    if finding_kwargs is None:
        return None

    finding = AnomalyFinding(
        anomaly_rule_id=rule.id,
        metric_code=rule.metric_code,
        dedup_key=dedup_key,
        baseline_window_start=None,
        baseline_window_end=None,
        observed_window_start=observed_window.start,
        observed_window_end=observed_window.end,
        observed_value=observed,
        severity=rule.severity,
        status="open",
        **finding_kwargs,
    )
    session.add(finding)
    await session.flush()
    return finding


async def evaluate_all_active_rules(session: AsyncSession) -> list[AnomalyFinding]:
    rules = (
        await session.scalars(select(AnomalyRule).where(AnomalyRule.is_active.is_(True)))
    ).all()
    findings: list[AnomalyFinding] = []
    for rule in rules:
        finding = await evaluate_rule(session, rule)
        if finding is not None:
            findings.append(finding)
    return findings
