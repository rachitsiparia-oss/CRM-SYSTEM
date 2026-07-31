"""HTTP-layer permission tests for the achievements router.

`operations_manager` holds `achievements.view` only (situational
oversight); `marketing_manager` owns achievement definitions and holds
`achievements.manage` too. Business-rule correctness (award idempotency,
cooldowns, reversal) is covered by test_achievements_awards.py; this file
checks only the router's own responsibility: permission enforcement.
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


def _achievement_payload(**overrides: Any) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "code": f"ach-{suffix}",
        "name": f"Achievement {suffix}",
        "condition": {
            "kind": "condition",
            "fact": "customer.completed_order_count",
            "operator": "gte",
            "value": 0,
        },
    }
    payload.update(overrides)
    return payload


async def _create_achievement_via_api(authed_client: AsyncClient, marketer: StaffUser) -> str:
    response = await authed_client.post(
        "/api/v1/achievements", json=_achievement_payload(), headers=_headers(marketer)
    )
    assert response.status_code == 201, response.text
    achievement_id: str = response.json()["data"]["id"]
    return achievement_id


# --- Authentication ------------------------------------------------------


async def test_list_achievements_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/achievements")
    assert response.status_code == 401


# --- achievements.view -----------------------------------------------------


async def test_list_achievements_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/achievements", headers=_headers(outsider))
    assert response.status_code == 403


async def test_list_achievements_succeeds_for_view_only_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.get("/api/v1/achievements", headers=_headers(viewer))
    assert response.status_code == 200, response.text


# --- achievements.manage -----------------------------------------------------


async def test_create_achievement_requires_manage_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/achievements", json=_achievement_payload(), headers=_headers(viewer)
    )
    assert response.status_code == 403


async def test_create_achievement_succeeds_for_manage_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    marketer = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/achievements", json=_achievement_payload(), headers=_headers(marketer)
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["is_active"] is True


async def test_evaluate_and_award_requires_manage_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    marketer = await make_staff_user(role_code="marketing_manager")
    achievement_id = await _create_achievement_via_api(authed_client, marketer)

    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/achievements/evaluate",
        json={
            "achievement_id": achievement_id,
            "customer_id": str(uuid.uuid4()),
            "source_event_type": "order.completed",
            "source_event_key": f"order-{uuid.uuid4().hex}",
        },
        headers=_headers(viewer),
    )
    assert response.status_code == 403


async def test_reverse_award_requires_manage_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        f"/api/v1/achievements/awards/{uuid.uuid4()}/reverse",
        json={"reason": "mistake"},
        headers=_headers(viewer),
    )
    assert response.status_code == 403


# --- 404 ---------------------------------------------------------------


async def test_get_unknown_achievement_returns_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get(
        f"/api/v1/achievements/{uuid.uuid4()}", headers=_headers(owner)
    )
    assert response.status_code == 404


async def test_get_unknown_award_returns_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get(
        f"/api/v1/achievements/awards/{uuid.uuid4()}", headers=_headers(owner)
    )
    assert response.status_code == 404
