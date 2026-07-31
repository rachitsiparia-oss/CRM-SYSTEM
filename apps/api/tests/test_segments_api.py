"""HTTP-layer permission tests for the segments router.

`operations_manager` has `segments.view` only (situational oversight);
`marketing_manager` owns the domain and holds `segments.view`,
`segments.manage`, and `segments.refresh` — see
app/permissions/role_matrix.py's own comments for that split. Business-rule
correctness (state machine, membership history, refresh math) is covered by
test_segments_service.py; this file checks only the router's own
responsibility: permission enforcement.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


def _static_segment_payload(**overrides: Any) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "code": f"seg-{suffix}",
        "name": f"Segment {suffix}",
        "segment_type": "static",
    }
    payload.update(overrides)
    return payload


async def _create_static_segment(authed_client: AsyncClient, owner: StaffUser) -> str:
    response = await authed_client.post(
        "/api/v1/segments", json=_static_segment_payload(), headers=_headers(owner)
    )
    assert response.status_code == 201, response.text
    segment_id: str = response.json()["data"]["id"]
    return segment_id


# --- Authentication ------------------------------------------------------


async def test_list_segments_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/segments")
    assert response.status_code == 401


# --- segments.view -----------------------------------------------------------


async def test_list_segments_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/segments", headers=_headers(outsider))
    assert response.status_code == 403


async def test_list_segments_succeeds_for_view_only_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.get("/api/v1/segments", headers=_headers(viewer))
    assert response.status_code == 200, response.text


# --- segments.manage -----------------------------------------------------


async def test_create_segment_requires_manage_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # operations_manager has segments.view but not segments.manage.
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/segments", json=_static_segment_payload(), headers=_headers(viewer)
    )
    assert response.status_code == 403


async def test_create_segment_succeeds_for_manage_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    marketer = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/segments", json=_static_segment_payload(), headers=_headers(marketer)
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["status"] == "draft"


async def test_add_member_requires_manage_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    segment_id = await _create_static_segment(authed_client, owner)

    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        f"/api/v1/segments/{segment_id}/members",
        json={"customer_id": str(uuid.uuid4())},
        headers=_headers(viewer),
    )
    assert response.status_code == 403


# --- segments.refresh -----------------------------------------------------


async def test_refresh_requires_dedicated_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    response = await authed_client.post(
        "/api/v1/segments",
        json={
            "code": f"seg-{uuid.uuid4().hex[:10]}",
            "name": "Dynamic",
            "segment_type": "dynamic",
            "rule_definition": {
                "kind": "condition",
                "fact": "customer.completed_order_count",
                "operator": "gte",
                "value": 0,
            },
        },
        headers=_headers(owner),
    )
    assert response.status_code == 201, response.text
    segment_id = response.json()["data"]["id"]

    # marketing_manager has segments.manage but this endpoint requires the
    # dedicated segments.refresh permission — verify a manage-only-esque
    # role without it (operations_manager has neither) is rejected too.
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        f"/api/v1/segments/{segment_id}/refresh", headers=_headers(viewer)
    )
    assert response.status_code == 403


async def test_refresh_succeeds_for_role_with_refresh_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    marketer = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/segments",
        json={
            "code": f"seg-{uuid.uuid4().hex[:10]}",
            "name": "Dynamic",
            "segment_type": "dynamic",
            "rule_definition": {
                "kind": "condition",
                "fact": "customer.completed_order_count",
                "operator": "gte",
                "value": 0,
            },
        },
        headers=_headers(marketer),
    )
    assert response.status_code == 201, response.text
    segment_id = response.json()["data"]["id"]

    refresh_response = await authed_client.post(
        f"/api/v1/segments/{segment_id}/refresh", headers=_headers(marketer)
    )
    assert refresh_response.status_code == 200, refresh_response.text
    assert refresh_response.json()["data"]["segment_id"] == segment_id


# --- 404 ---------------------------------------------------------------


async def test_get_unknown_segment_returns_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get(f"/api/v1/segments/{uuid.uuid4()}", headers=_headers(owner))
    assert response.status_code == 404
