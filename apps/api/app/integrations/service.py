"""Integration registry CRUD — INTEGRATIONS_AUTOMATIONS_REALTIME.md
sections 4/5. Configuration for the integrations this table describes
(communication channels, AI provider selection) still lives where it
always has (`CommunicationChannel`, environment variables read by
`app.controlled_ai.providers`) — this table is the read-mostly summary/
health record layered on top, not a second place that owns the actual
configuration. `pause`/`resume`/`disable` only ever change this row's own
`status`/`is_enabled`; they never touch the underlying channel/provider
configuration.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Integration, StaffUser
from app.integrations.errors import IntegrationNotFoundError


async def list_integrations(
    session: AsyncSession, *, category: str | None = None, health_state: str | None = None
) -> list[Integration]:
    conditions = []
    if category is not None:
        conditions.append(Integration.category == category)
    if health_state is not None:
        conditions.append(Integration.health_state == health_state)
    rows = await session.scalars(
        select(Integration).where(*conditions).order_by(Integration.display_name)
    )
    return list(rows.all())


async def get_integration(session: AsyncSession, integration_id: uuid.UUID) -> Integration:
    integration = await session.get(Integration, integration_id)
    if integration is None:
        raise IntegrationNotFoundError(f"Integration {integration_id} not found.")
    return integration


async def get_integration_by_code(session: AsyncSession, code: str) -> Integration | None:
    result: Integration | None = await session.scalar(
        select(Integration).where(Integration.code == code)
    )
    return result


async def pause_integration(
    session: AsyncSession, *, integration: Integration, actor: StaffUser
) -> Integration:
    integration.status = "paused"
    integration.is_enabled = False
    integration.updated_by = actor.id
    await session.flush()
    return integration


async def resume_integration(
    session: AsyncSession, *, integration: Integration, actor: StaffUser
) -> Integration:
    integration.status = "active" if integration.health_state == "healthy" else "degraded"
    integration.is_enabled = True
    integration.updated_by = actor.id
    await session.flush()
    return integration


async def disable_integration(
    session: AsyncSession, *, integration: Integration, actor: StaffUser
) -> Integration:
    integration.status = "disabled"
    integration.is_enabled = False
    integration.updated_by = actor.id
    await session.flush()
    return integration


async def record_health_result(
    session: AsyncSession,
    *,
    integration: Integration,
    healthy: bool,
    error_category: str | None = None,
) -> Integration:
    now = datetime.now(UTC)
    if healthy:
        integration.health_state = "healthy"
        integration.last_success_at = now
        if integration.status in ("degraded", "failed", "validating", "draft"):
            integration.status = "active"
    else:
        integration.health_state = "unhealthy" if integration.status == "active" else "degraded"
        integration.last_failure_at = now
        integration.last_error_category = error_category
        if integration.status == "active":
            integration.status = "degraded"
    await session.flush()
    return integration
