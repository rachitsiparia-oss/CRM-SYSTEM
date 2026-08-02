"""HTTP-layer permission tests for the Phase 15 routers (jobs, scheduler,
dead-letter, integrations, feature-flags, operational-settings, event-log,
cache). Business-rule correctness for each domain is covered by its own
service-level test file; this file checks only each router's own
responsibility: authentication is required, the right permission code
gates access, and `owner` (which holds every permission) can reach it.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


# --- Authentication --------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/jobs",
        "/api/v1/scheduler",
        "/api/v1/dead-letter",
        "/api/v1/integrations",
        "/api/v1/feature-flags",
        "/api/v1/operational-settings",
        "/api/v1/event-log",
        "/api/v1/cache/families",
    ],
)
async def test_endpoint_requires_authentication(authed_client: AsyncClient, path: str) -> None:
    response = await authed_client.get(path)
    assert response.status_code == 401


# --- Permission enforcement -------------------------------------------------


async def test_list_jobs_requires_jobs_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/jobs", headers=_headers(outsider))
    assert response.status_code == 403

    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get("/api/v1/jobs", headers=_headers(owner))
    assert response.status_code == 200
    assert "pagination" in response.json()


async def test_scheduler_get_requires_scheduler_view_and_patch_requires_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    assert (
        await authed_client.get("/api/v1/scheduler", headers=_headers(outsider))
    ).status_code == 403

    owner = await make_staff_user(role_code="owner")
    get_response = await authed_client.get("/api/v1/scheduler", headers=_headers(owner))
    assert get_response.status_code == 200
    body = get_response.json()["data"]
    assert "scheduler_enabled" in body
    assert isinstance(body["jobs"], list)
    assert len(body["jobs"]) > 0

    patch_response = await authed_client.patch(
        "/api/v1/scheduler", json={"scheduler_enabled": True}, headers=_headers(owner)
    )
    assert patch_response.status_code == 200


async def test_dead_letter_requires_dead_letter_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/dead-letter", headers=_headers(outsider))
    assert response.status_code == 403

    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get("/api/v1/dead-letter", headers=_headers(owner))
    assert response.status_code == 200


async def test_integrations_list_requires_settings_integrations_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/integrations", headers=_headers(outsider))
    assert response.status_code == 403

    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get("/api/v1/integrations", headers=_headers(owner))
    assert response.status_code == 200
    assert len(response.json()["data"]) > 0  # seeded rows


async def test_feature_flags_create_requires_settings_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    payload = {"code": f"test.perm.{uuid.uuid4().hex[:8]}", "name": "Test"}
    response = await authed_client.post(
        "/api/v1/feature-flags", json=payload, headers=_headers(outsider)
    )
    assert response.status_code == 403

    owner = await make_staff_user(role_code="owner")
    payload = {"code": f"test.perm.{uuid.uuid4().hex[:8]}", "name": "Test"}
    response = await authed_client.post(
        "/api/v1/feature-flags", json=payload, headers=_headers(owner)
    )
    assert response.status_code == 201


async def test_operational_settings_get_requires_settings_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/operational-settings", headers=_headers(outsider))
    assert response.status_code == 403

    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get("/api/v1/operational-settings", headers=_headers(owner))
    assert response.status_code == 200  # seeded singleton row exists


async def test_cache_invalidate_requires_cache_invalidate(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.post(
        "/api/v1/cache/invalidate", json={"family": "settings"}, headers=_headers(outsider)
    )
    assert response.status_code == 403

    owner = await make_staff_user(role_code="owner")
    response = await authed_client.post(
        "/api/v1/cache/invalidate", json={"family": "settings"}, headers=_headers(owner)
    )
    assert response.status_code == 200
    assert "keys_removed" in response.json()["data"]


async def test_metrics_endpoint_is_unauthenticated(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
