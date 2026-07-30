import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.db.models import StaffUser
from app.notifications.service import notify
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def test_notify_dedup_key_prevents_duplicates(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user()
    dedup_key = f"test-dedup-{uuid.uuid4().hex}"

    first = await notify(
        db_session,
        notification_type="task.assigned",
        title="First",
        recipient_staff_id=staff_user.id,
        dedup_key=dedup_key,
    )
    second = await notify(
        db_session,
        notification_type="task.assigned",
        title="Second (should be a no-op)",
        recipient_staff_id=staff_user.id,
        dedup_key=dedup_key,
    )
    assert first is not None
    assert second is None


async def test_notify_without_dedup_key_always_creates(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user()
    first = await notify(
        db_session, notification_type="task.assigned", title="A", recipient_staff_id=staff_user.id
    )
    second = await notify(
        db_session, notification_type="task.assigned", title="B", recipient_staff_id=staff_user.id
    )
    assert first is not None
    assert second is not None
    assert first.id != second.id


async def test_list_notifications_only_shows_own(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user()
    other_staff = await make_staff_user()

    await notify(
        db_session,
        notification_type="task.assigned",
        title="Mine",
        recipient_staff_id=staff_user.id,
    )
    await notify(
        db_session,
        notification_type="task.assigned",
        title="Not mine",
        recipient_staff_id=other_staff.id,
    )

    response = await authed_client.get("/api/v1/notifications", headers=_headers(staff_user))
    assert response.status_code == 200
    titles = [n["title"] for n in response.json()["data"]]
    assert "Mine" in titles
    assert "Not mine" not in titles


async def test_mark_read_only_own_notification(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user()
    other = await make_staff_user()
    notification = await notify(
        db_session, notification_type="task.assigned", title="Mine", recipient_staff_id=owner.id
    )
    assert notification is not None

    forbidden_response = await authed_client.post(
        f"/api/v1/notifications/{notification.id}/read", headers=_headers(other)
    )
    assert forbidden_response.status_code == 404

    ok_response = await authed_client.post(
        f"/api/v1/notifications/{notification.id}/read", headers=_headers(owner)
    )
    assert ok_response.status_code == 200
    assert ok_response.json()["data"]["read_at"] is not None


async def test_unread_count(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user()
    await notify(
        db_session, notification_type="task.assigned", title="A", recipient_staff_id=staff_user.id
    )
    await notify(
        db_session, notification_type="task.assigned", title="B", recipient_staff_id=staff_user.id
    )

    response = await authed_client.get(
        "/api/v1/notifications/unread-count", headers=_headers(staff_user)
    )
    assert response.status_code == 200
    assert response.json()["data"] == 2


async def test_broadcast_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    other = await make_staff_user()
    response = await authed_client.post(
        "/api/v1/notifications/broadcast",
        json={"recipient_staff_ids": [str(other.id)], "title": "Announcement"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


async def test_broadcast_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    recipient1 = await make_staff_user()
    recipient2 = await make_staff_user()
    response = await authed_client.post(
        "/api/v1/notifications/broadcast",
        json={
            "recipient_staff_ids": [str(recipient1.id), str(recipient2.id)],
            "title": "Staff meeting at 5pm",
        },
        headers=_headers(staff_user),
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 2
