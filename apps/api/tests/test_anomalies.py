"""Tests for `app.anomalies` — rule evaluation short-circuits (inactive,
cooldown) and the finding lifecycle state machine."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from app.anomalies.engine import evaluate_rule
from app.anomalies.errors import InvalidAnomalyTransitionError
from app.anomalies.service import transition_finding
from app.db.models import AnomalyFinding, AnomalyRule, StaffUser
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _make_rule(**overrides: object) -> AnomalyRule:
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": f"test-rule-{uuid.uuid4().hex[:8]}",
        "name": "Test rule",
        "metric_code": "inventory_critical_stock_items",
        "rule_type": "absolute_threshold",
        "comparison_operator": "gt",
        "threshold_value": 5,
        "minimum_sample_size": 1,
        "cooldown_hours": 24,
        "severity": "high",
        "is_active": True,
        "notify_task": False,
    }
    fields.update(overrides)
    return AnomalyRule(**fields)


async def test_evaluate_rule_skips_inactive_rule(db_session: AsyncSession) -> None:
    rule = _make_rule(is_active=False)
    db_session.add(rule)
    await db_session.flush()
    finding = await evaluate_rule(db_session, rule)
    assert finding is None


async def test_evaluate_rule_respects_cooldown(db_session: AsyncSession) -> None:
    rule = _make_rule(cooldown_hours=24)
    db_session.add(rule)
    await db_session.flush()

    # A recent finding for this rule should suppress a new evaluation
    # regardless of what the metric would otherwise report.
    db_session.add(
        AnomalyFinding(
            id=uuid.uuid4(),
            anomaly_rule_id=rule.id,
            metric_code=rule.metric_code,
            dedup_key=f"{rule.id}:cooldown-probe",
            observed_window_start=datetime.now(UTC) - timedelta(hours=1),
            observed_window_end=datetime.now(UTC),
            severity="high",
            status="open",
        )
    )
    await db_session.flush()

    finding = await evaluate_rule(db_session, rule)
    assert finding is None


async def test_evaluate_rule_absolute_threshold_not_breached_returns_none(
    db_session: AsyncSession,
) -> None:
    # Threshold absurdly high — no seeded/created data can breach it.
    rule = _make_rule(threshold_value=999999, cooldown_hours=0)
    db_session.add(rule)
    await db_session.flush()
    finding = await evaluate_rule(db_session, rule)
    assert finding is None


def _make_finding(anomaly_rule_id: uuid.UUID, **overrides: object) -> AnomalyFinding:
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "anomaly_rule_id": anomaly_rule_id,
        "metric_code": "inventory_critical_stock_items",
        "dedup_key": f"finding-{uuid.uuid4().hex[:8]}",
        "observed_window_start": datetime.now(UTC) - timedelta(days=1),
        "observed_window_end": datetime.now(UTC),
        "severity": "high",
        "status": "open",
    }
    fields.update(overrides)
    return AnomalyFinding(**fields)


async def _make_persisted_rule(db_session: AsyncSession) -> AnomalyRule:
    rule = _make_rule()
    db_session.add(rule)
    await db_session.flush()
    return rule


async def test_transition_finding_open_to_acknowledged(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    rule = await _make_persisted_rule(db_session)
    finding = _make_finding(rule.id)
    db_session.add(finding)
    await db_session.flush()

    updated = await transition_finding(
        db_session, actor=actor, finding=finding, target_status="acknowledged"
    )
    assert updated.status == "acknowledged"
    assert updated.acknowledged_by == actor.id
    assert updated.acknowledged_at is not None


async def test_transition_finding_rejects_invalid_transition(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    rule = await _make_persisted_rule(db_session)
    finding = _make_finding(rule.id, status="resolved")
    db_session.add(finding)
    await db_session.flush()

    with pytest.raises(InvalidAnomalyTransitionError):
        await transition_finding(
            db_session, actor=actor, finding=finding, target_status="acknowledged"
        )


async def test_transition_finding_dismissed_records_resolution_note(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    rule = await _make_persisted_rule(db_session)
    finding = _make_finding(rule.id)
    db_session.add(finding)
    await db_session.flush()

    updated = await transition_finding(
        db_session,
        actor=actor,
        finding=finding,
        target_status="dismissed",
        resolution_note="False positive.",
    )
    assert updated.status == "dismissed"
    assert updated.resolved_by == actor.id
    assert updated.resolution_note == "False positive."
