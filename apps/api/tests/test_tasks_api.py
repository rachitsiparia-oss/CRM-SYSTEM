from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _create_task(
    authed_client: AsyncClient, staff_user: StaffUser, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"title": "Restock napkins", "source": "manual"}
    payload.update(overrides)
    response = await authed_client.post("/api/v1/tasks", json=payload, headers=_headers(staff_user))
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()["data"]
    return result


async def test_create_task_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="delivery_coordinator")
    response = await authed_client.post(
        "/api/v1/tasks",
        json={"title": "Test task", "source": "manual"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


async def test_create_task_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    task = await _create_task(authed_client, staff_user)
    assert task["status"] == "open"
    assert task["priority"] == "normal"


async def test_recurring_template_requires_rule(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/tasks",
        json={
            "title": "Weekly deep clean",
            "source": "manual",
            "is_recurring_template": True,
        },
        headers=_headers(staff_user),
    )
    assert response.status_code == 422


async def test_complete_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    creator = await make_staff_user(role_code="operations_manager")
    task = await _create_task(authed_client, creator)

    no_complete_role = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        f"/api/v1/tasks/{task['id']}/transition",
        json={"target_status": "completed"},
        headers=_headers(no_complete_role),
    )
    assert response.status_code == 403


async def test_complete_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    task = await _create_task(authed_client, staff_user)

    response = await authed_client.post(
        f"/api/v1/tasks/{task['id']}/transition",
        json={"target_status": "completed", "completion_notes": "Done."},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "completed"


async def test_blocked_requires_reason(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    task = await _create_task(authed_client, staff_user)

    response = await authed_client.post(
        f"/api/v1/tasks/{task['id']}/transition",
        json={"target_status": "blocked"},
        headers=_headers(staff_user),
    )
    assert response.status_code in (409, 422)


async def test_assign_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    creator = await make_staff_user(role_code="operations_manager")
    task = await _create_task(authed_client, creator)

    no_assign_role = await make_staff_user(role_code="marketing_manager")
    other_staff = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/tasks/{task['id']}/assign",
        json={"assigned_staff_id": str(other_staff.id)},
        headers=_headers(no_assign_role),
    )
    assert response.status_code == 403


async def test_assign_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    creator = await make_staff_user(role_code="operations_manager")
    task = await _create_task(authed_client, creator)

    assignee = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/tasks/{task['id']}/assign",
        json={"assigned_staff_id": str(assignee.id)},
        headers=_headers(creator),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["assigned_staff_id"] == str(assignee.id)


async def test_only_own_tasks_visible_without_view_all(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner_role = await make_staff_user(role_code="operations_manager")
    await _create_task(authed_client, owner_role)

    limited_role = await make_staff_user(role_code="kitchen_staff")
    await _create_task(
        authed_client,
        owner_role,
        title="Someone else's task",
        assigned_staff_id=str(limited_role.id),
    )

    response = await authed_client.get("/api/v1/tasks", headers=_headers(limited_role))
    assert response.status_code == 200
    titles = [t["title"] for t in response.json()["data"]]
    assert "Someone else's task" in titles
    assert "Restock napkins" not in titles


async def test_overdue_view_filter(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    overdue_due = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    task = await _create_task(authed_client, staff_user, due_at=overdue_due, title="Overdue task")

    response = await authed_client.get(
        "/api/v1/tasks", params={"view": "overdue"}, headers=_headers(staff_user)
    )
    assert response.status_code == 200
    ids = [t["id"] for t in response.json()["data"]]
    assert task["id"] in ids
