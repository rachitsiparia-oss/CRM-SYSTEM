"""HTTP-layer permission tests for the campaigns router, focused on
`app/campaigns/router.py`'s `_TRANSITION_PERMISSION_OVERRIDES`:

    {"scheduled": "campaigns.approve", "running": "campaigns.execute",
     "paused": "campaigns.cancel", "cancelled": "campaigns.cancel"}

moving a campaign into `scheduled` or `running` needs the listed elevated
permission *in addition to* the baseline `campaigns.manage` the endpoint
already requires — not just `campaigns.manage` alone. No seeded system role
holds `campaigns.manage` without also holding every override permission
(only `marketing_manager` and `owner` have `campaigns.manage` at all, and
`marketing_manager` has the full set — see `app/permissions/role_matrix.py`),
so a scoped test-only role is built directly against the permission tables
to isolate exactly `campaigns.manage` (and, for the second override, exactly
`campaigns.manage` + `campaigns.approve`) the same way
`tests/test_staff_models.py` already manipulates `RolePermission` directly.
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from app.db.models import (
    CommunicationChannel,
    Permission,
    Role,
    RolePermission,
    StaffRole,
    StaffUser,
)
from app.permissions.service import invalidate_permissions_cache
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _make_scoped_staff_user(
    session: AsyncSession, make_staff_user: MakeStaffUser, *, permission_codes: tuple[str, ...]
) -> StaffUser:
    staff_user = await make_staff_user(role_code=None)
    suffix = uuid.uuid4().hex[:10]
    role = Role(id=uuid.uuid4(), code=f"test-scoped-{suffix}", name=f"Test scoped role {suffix}")
    session.add(role)
    await session.flush()
    for code in permission_codes:
        permission_id = await session.scalar(select(Permission.id).where(Permission.code == code))
        assert permission_id is not None, f"Permission {code!r} is not seeded."
        session.add(RolePermission(role_id=role.id, permission_id=permission_id, scope_type="all"))
    session.add(
        StaffRole(staff_user_id=staff_user.id, role_id=role.id, assigned_at=datetime.now(UTC))
    )
    await session.flush()
    await invalidate_permissions_cache(staff_user.id)
    return staff_user


async def _get_or_create_channel(
    session: AsyncSession, *, code: str = "email"
) -> CommunicationChannel:
    existing = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.code == code)
    )
    if existing is not None:
        return existing
    channel = CommunicationChannel(id=uuid.uuid4(), code=code, name=code.title())
    session.add(channel)
    await session.flush()
    return channel


def _campaign_payload(
    *, segment_id: str, channel_id: uuid.UUID, **overrides: Any
) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "code": f"camp-{suffix}",
        "name": "Test Campaign",
        "channel_templates": {str(channel_id): str(uuid.uuid4())},
        "target_segment_ids": [segment_id],
    }
    payload.update(overrides)
    return payload


async def _create_campaign(
    authed_client: AsyncClient, staff_user: StaffUser, *, segment_id: str, channel_id: uuid.UUID
) -> dict[str, Any]:
    response = await authed_client.post(
        "/api/v1/campaigns",
        json=_campaign_payload(segment_id=segment_id, channel_id=channel_id),
        headers=_headers(staff_user),
    )
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


async def _transition(
    authed_client: AsyncClient, staff_user: StaffUser, *, campaign_id: str, target_status: str
) -> Any:
    return await authed_client.post(
        f"/api/v1/campaigns/{campaign_id}/transition",
        json={"target_status": target_status},
        headers=_headers(staff_user),
    )


# --- baseline authentication/authorization ----------------------------------


async def test_list_campaigns_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/campaigns")
    assert response.status_code == 401


async def test_list_campaigns_requires_campaigns_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/campaigns", headers=_headers(outsider))
    assert response.status_code == 403


async def test_create_campaign_requires_campaigns_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # operations_manager has campaigns.view but not campaigns.manage.
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/campaigns",
        json=_campaign_payload(segment_id=str(uuid.uuid4()), channel_id=uuid.uuid4()),
        headers=_headers(viewer),
    )
    assert response.status_code == 403


# --- transition override permissions ----------------------------------------


async def test_transition_to_scheduled_requires_campaigns_approve_not_just_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    manage_only = await _make_scoped_staff_user(
        db_session, make_staff_user, permission_codes=("campaigns.manage",)
    )
    channel = await _get_or_create_channel(db_session)
    segment_id = str(uuid.uuid4())
    campaign = await _create_campaign(
        authed_client, manage_only, segment_id=segment_id, channel_id=channel.id
    )

    # draft -> ready is not in the override map: campaigns.manage alone suffices.
    ready_response = await _transition(
        authed_client, manage_only, campaign_id=campaign["id"], target_status="ready"
    )
    assert ready_response.status_code == 200, ready_response.text

    # ready -> scheduled IS in the override map: campaigns.manage alone must not suffice.
    scheduled_response = await _transition(
        authed_client, manage_only, campaign_id=campaign["id"], target_status="scheduled"
    )
    assert scheduled_response.status_code == 403


async def test_transition_to_scheduled_succeeds_with_campaigns_approve(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    manager = await _make_scoped_staff_user(
        db_session,
        make_staff_user,
        permission_codes=("campaigns.manage", "campaigns.approve"),
    )
    channel = await _get_or_create_channel(db_session)
    segment_id = str(uuid.uuid4())
    campaign = await _create_campaign(
        authed_client, manager, segment_id=segment_id, channel_id=channel.id
    )
    await _transition(authed_client, manager, campaign_id=campaign["id"], target_status="ready")

    scheduled_response = await _transition(
        authed_client, manager, campaign_id=campaign["id"], target_status="scheduled"
    )
    assert scheduled_response.status_code == 200, scheduled_response.text
    assert scheduled_response.json()["data"]["status"] == "scheduled"


async def test_transition_to_running_requires_campaigns_execute_not_just_approve(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    manage_and_approve = await _make_scoped_staff_user(
        db_session,
        make_staff_user,
        permission_codes=("campaigns.manage", "campaigns.approve"),
    )
    channel = await _get_or_create_channel(db_session)
    segment_id = str(uuid.uuid4())
    campaign = await _create_campaign(
        authed_client, manage_and_approve, segment_id=segment_id, channel_id=channel.id
    )
    await _transition(
        authed_client, manage_and_approve, campaign_id=campaign["id"], target_status="ready"
    )
    await _transition(
        authed_client, manage_and_approve, campaign_id=campaign["id"], target_status="scheduled"
    )

    running_response = await _transition(
        authed_client, manage_and_approve, campaign_id=campaign["id"], target_status="running"
    )
    assert running_response.status_code == 403


async def test_full_transition_flow_succeeds_for_owner(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    channel = await _get_or_create_channel(db_session)
    segment_id = str(uuid.uuid4())
    campaign = await _create_campaign(
        authed_client, owner, segment_id=segment_id, channel_id=channel.id
    )

    for target in ("ready", "scheduled", "running", "completed", "archived"):
        response = await _transition(
            authed_client, owner, campaign_id=campaign["id"], target_status=target
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["status"] == target
