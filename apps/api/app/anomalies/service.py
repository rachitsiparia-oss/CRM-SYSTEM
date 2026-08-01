"""Anomaly rule CRUD and finding lifecycle — GROWTH_AND_INTELLIGENCE.md
section 15.7's "acknowledgement state"."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.registry import get_metric
from app.anomalies.errors import AnomalyError, InvalidAnomalyTransitionError
from app.core.pagination import DEFAULT_PAGE_SIZE
from app.db.models import AnomalyFinding, AnomalyRule, StaffUser

_VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "open": ("acknowledged", "dismissed"),
    "acknowledged": ("investigating", "resolved", "dismissed"),
    "investigating": ("resolved", "dismissed"),
    "resolved": (),
    "dismissed": (),
}


async def create_rule(session: AsyncSession, *, actor: StaffUser, payload: object) -> AnomalyRule:
    from app.anomalies.schemas import AnomalyRuleCreateIn

    assert isinstance(payload, AnomalyRuleCreateIn)
    try:
        get_metric(payload.metric_code)
    except KeyError as exc:
        raise AnomalyError(f"Unknown metric code: {payload.metric_code!r}") from exc

    rule = AnomalyRule(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        metric_code=payload.metric_code,
        rule_type=payload.rule_type,
        comparison_operator=payload.comparison_operator,
        threshold_value=payload.threshold_value,
        rolling_window_periods=payload.rolling_window_periods,
        minimum_sample_size=payload.minimum_sample_size,
        cooldown_hours=payload.cooldown_hours,
        severity=payload.severity,
        is_active=payload.is_active,
        notify_task=payload.notify_task,
        notify_role_code=payload.notify_role_code,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(rule)
    await session.flush()
    return rule


async def update_rule(
    session: AsyncSession, *, actor: StaffUser, rule: AnomalyRule, payload: object
) -> AnomalyRule:
    from app.anomalies.schemas import AnomalyRuleUpdateIn

    assert isinstance(payload, AnomalyRuleUpdateIn)
    for field_name in (
        "name",
        "description",
        "comparison_operator",
        "threshold_value",
        "rolling_window_periods",
        "minimum_sample_size",
        "cooldown_hours",
        "severity",
        "is_active",
        "notify_task",
        "notify_role_code",
    ):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(rule, field_name, value)
    rule.updated_by = actor.id
    rule.version += 1
    await session.flush()
    return rule


async def list_rules(session: AsyncSession, *, is_active: bool | None = None) -> list[AnomalyRule]:
    conditions = []
    if is_active is not None:
        conditions.append(AnomalyRule.is_active == is_active)
    rows = await session.scalars(select(AnomalyRule).where(*conditions).order_by(AnomalyRule.name))
    return list(rows.all())


async def get_rule(session: AsyncSession, rule_id: uuid.UUID) -> AnomalyRule | None:
    return await session.get(AnomalyRule, rule_id)


async def get_finding(session: AsyncSession, finding_id: uuid.UUID) -> AnomalyFinding | None:
    return await session.get(AnomalyFinding, finding_id)


async def list_findings(
    session: AsyncSession,
    *,
    status_filter: str | None = None,
    severity: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[AnomalyFinding], int]:
    conditions = []
    if status_filter is not None:
        conditions.append(AnomalyFinding.status == status_filter)
    if severity is not None:
        conditions.append(AnomalyFinding.severity == severity)
    total = (
        await session.scalar(select(func.count()).select_from(AnomalyFinding).where(*conditions))
    ) or 0
    rows = await session.scalars(
        select(AnomalyFinding)
        .where(*conditions)
        .order_by(AnomalyFinding.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.all()), total


async def transition_finding(
    session: AsyncSession,
    *,
    actor: StaffUser,
    finding: AnomalyFinding,
    target_status: str,
    resolution_note: str | None = None,
) -> AnomalyFinding:
    allowed = _VALID_TRANSITIONS.get(finding.status, ())
    if target_status not in allowed:
        raise InvalidAnomalyTransitionError(
            f"Cannot transition an anomaly finding from {finding.status!r} to {target_status!r}."
        )
    now = datetime.now(UTC)
    finding.status = target_status
    if target_status == "acknowledged":
        finding.acknowledged_by = actor.id
        finding.acknowledged_at = now
    if target_status in ("resolved", "dismissed"):
        finding.resolved_by = actor.id
        finding.resolved_at = now
        if resolution_note is not None:
            finding.resolution_note = resolution_note
    await session.flush()
    return finding
