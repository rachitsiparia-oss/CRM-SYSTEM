"""Tests for `app.integrations` — the registry's pause/resume/disable
state transitions and `record_health_result`'s status recovery."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from app.db.models import Integration, StaffUser
from app.integrations.service import (
    disable_integration,
    get_integration_by_code,
    list_integrations,
    pause_integration,
    record_health_result,
    resume_integration,
)
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def _make_integration(session: AsyncSession, actor: StaffUser) -> Integration:
    code = f"test-integration-{uuid.uuid4().hex[:8]}"
    integration = Integration(
        code=code,
        category="email",
        provider_code="test-provider",
        display_name="Test Integration",
        status="active",
        is_enabled=True,
        health_state="healthy",
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(integration)
    await session.flush()
    return integration


async def test_pause_then_resume_round_trips_status(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    integration = await _make_integration(db_session, actor)

    paused = await pause_integration(db_session, integration=integration, actor=actor)
    assert paused.status == "paused"
    assert paused.is_enabled is False

    resumed = await resume_integration(db_session, integration=integration, actor=actor)
    assert resumed.is_enabled is True
    assert resumed.status == "active"  # health_state was already "healthy"


async def test_disable_integration_sets_disabled_and_unenabled(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    integration = await _make_integration(db_session, actor)

    disabled = await disable_integration(db_session, integration=integration, actor=actor)
    assert disabled.status == "disabled"
    assert disabled.is_enabled is False


async def test_record_health_result_recovers_a_degraded_integration(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    integration = await _make_integration(db_session, actor)

    unhealthy = await record_health_result(
        db_session, integration=integration, healthy=False, error_category="not_configured"
    )
    assert unhealthy.health_state == "unhealthy"
    assert unhealthy.status == "degraded"
    assert unhealthy.last_failure_at is not None

    recovered = await record_health_result(db_session, integration=integration, healthy=True)
    assert recovered.health_state == "healthy"
    assert recovered.status == "active"
    assert recovered.last_success_at is not None


async def test_list_integrations_filters_by_category(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    integration = await _make_integration(db_session, actor)

    rows = await list_integrations(db_session, category="email")
    assert any(r.id == integration.id for r in rows)

    rows = await list_integrations(db_session, category="whatsapp")
    assert all(r.id != integration.id for r in rows)


async def test_get_integration_by_code_returns_none_for_unknown_code(
    db_session: AsyncSession,
) -> None:
    result = await get_integration_by_code(db_session, f"never-seeded-{uuid.uuid4().hex[:8]}")
    assert result is None
