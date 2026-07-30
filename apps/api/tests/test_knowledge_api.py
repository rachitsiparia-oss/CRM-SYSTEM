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


async def _create_article(
    authed_client: AsyncClient, staff_user: StaffUser, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": "Test SOP",
        "content": "Do the thing safely.",
        "article_type": "sop",
    }
    payload.update(overrides)
    response = await authed_client.post(
        "/api/v1/knowledge/articles", json=payload, headers=_headers(staff_user)
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()["data"]
    return result


async def test_create_article_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="delivery_coordinator")
    response = await authed_client.post(
        "/api/v1/knowledge/articles",
        json={"title": "Test", "content": "Body", "article_type": "sop"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


async def test_full_lifecycle_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    article = await _create_article(authed_client, staff_user)
    assert article["status"] == "draft"

    submit = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/submit", headers=_headers(staff_user)
    )
    assert submit.status_code == 200, submit.text
    assert submit.json()["data"]["status"] == "in_review"

    # hr_manager is not privileged by default in this fixture, but is a
    # *different* actor than the author only in the self-approval test
    # below — here the same actor approving their own submission over a
    # non-privileged role should be rejected.
    approve = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/review",
        json={"target_status": "approved"},
        headers=_headers(staff_user),
    )
    assert approve.status_code == 403


async def test_self_approval_is_blocked_for_non_privileged_author(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    author = await make_staff_user(role_code="hr_manager")
    article = await _create_article(authed_client, author)
    await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/submit", headers=_headers(author)
    )
    response = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/review",
        json={"target_status": "approved"},
        headers=_headers(author),
    )
    assert response.status_code == 403


async def test_different_reviewer_can_approve_and_publish(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    author = await make_staff_user(role_code="hr_manager")
    reviewer = await make_staff_user(role_code="hr_manager")
    article = await _create_article(authed_client, author)
    await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/submit", headers=_headers(author)
    )
    approve = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/review",
        json={"target_status": "approved"},
        headers=_headers(reviewer),
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["data"]["status"] == "approved"

    publish = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/publish", headers=_headers(reviewer)
    )
    assert publish.status_code == 200, publish.text
    assert publish.json()["data"]["status"] == "published"


async def test_cannot_publish_without_approval(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    article = await _create_article(authed_client, staff_user)
    response = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/publish", headers=_headers(staff_user)
    )
    assert response.status_code == 409


async def test_hr_only_visibility_blocks_unauthorized_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    author = await make_staff_user(role_code="hr_manager")
    reviewer = await make_staff_user(role_code="hr_manager")
    article = await _create_article(authed_client, author, visibility_scope="hr_only")
    await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/submit", headers=_headers(author)
    )
    await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/review",
        json={"target_status": "approved"},
        headers=_headers(reviewer),
    )
    await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/publish", headers=_headers(reviewer)
    )

    outsider = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.get(
        f"/api/v1/knowledge/articles/{article['id']}", headers=_headers(outsider)
    )
    assert response.status_code == 403

    hr_viewer = await make_staff_user(role_code="hr_manager")
    response = await authed_client.get(
        f"/api/v1/knowledge/articles/{article['id']}", headers=_headers(hr_viewer)
    )
    assert response.status_code == 200


async def test_category_ancestry_cycle_is_rejected(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    category_a = await authed_client.post(
        "/api/v1/knowledge/categories",
        json={"name": "A", "code": f"cat-a-{staff_user.id.hex[:8]}"},
        headers=_headers(staff_user),
    )
    assert category_a.status_code == 201, category_a.text
    category_b = await authed_client.post(
        "/api/v1/knowledge/categories",
        json={
            "name": "B",
            "code": f"cat-b-{staff_user.id.hex[:8]}",
            "parent_id": category_a.json()["data"]["id"],
        },
        headers=_headers(staff_user),
    )
    assert category_b.status_code == 201, category_b.text

    response = await authed_client.patch(
        f"/api/v1/knowledge/categories/{category_a.json()['data']['id']}",
        json={"parent_id": category_b.json()["data"]["id"], "version": 1},
        headers=_headers(staff_user),
    )
    assert response.status_code == 409


async def test_mandatory_acknowledgement_flow(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    author = await make_staff_user(role_code="hr_manager")
    reviewer = await make_staff_user(role_code="hr_manager")
    article = await _create_article(authed_client, author, requires_acknowledgement=True)
    await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/submit", headers=_headers(author)
    )
    await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/review",
        json={"target_status": "approved"},
        headers=_headers(reviewer),
    )
    await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/publish", headers=_headers(reviewer)
    )

    assignee = await make_staff_user(role_code="kitchen_staff")
    assign = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/assignments",
        json={"assignee_type": "staff", "staff_id": str(assignee.id), "is_mandatory": True},
        headers=_headers(author),
    )
    assert assign.status_code == 201, assign.text

    ack = await authed_client.post(
        f"/api/v1/knowledge/articles/{article['id']}/acknowledge", headers=_headers(assignee)
    )
    assert ack.status_code == 200, ack.text
    assert ack.json()["data"]["acknowledged_at"] is not None


async def test_analytics_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.get("/api/v1/knowledge/analytics", headers=_headers(staff_user))
    assert response.status_code == 403

    manager = await make_staff_user(role_code="hr_manager")
    response = await authed_client.get("/api/v1/knowledge/analytics", headers=_headers(manager))
    assert response.status_code == 200
