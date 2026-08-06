from collections.abc import Awaitable, Callable

import pytest
from app.db.models import AuditEvent, StaffUser
from app.permissions.dependencies import (
    _PERMISSION_DENIAL_LIMIT,
    _PERMISSION_DENIAL_WINDOW_SECONDS,
)
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]

# kitchen_staff has no roles.* permission — SECURITY_PERFORMANCE_AND_QUALITY.md's
# role matrix / app.permissions.role_matrix.ROLE_PERMISSIONS["kitchen_staff"].
_DENIED_PATH = "/api/v1/roles"


async def test_repeated_permission_denials_auto_lock_the_account(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    token = make_access_token(staff_user.auth_user_id)
    headers = {"Authorization": f"Bearer {token}"}

    # First _PERMISSION_DENIAL_LIMIT denials stay under the threshold.
    for _ in range(_PERMISSION_DENIAL_LIMIT):
        response = await authed_client.get(_DENIED_PATH, headers=headers)
        assert response.status_code == 403
        assert (
            response.json()["error"]["message"]
            == "You do not have permission to perform this action."
        )

    await db_session.refresh(staff_user)
    assert staff_user.account_status == "active"

    # The next (11th) denial crosses the threshold and locks the account.
    response = await authed_client.get(_DENIED_PATH, headers=headers)
    assert response.status_code == 403

    await db_session.refresh(staff_user)
    assert staff_user.account_status == "locked"

    lock_event = await db_session.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.action_code == "auth.account_locked",
            AuditEvent.target_id == staff_user.id,
        )
        .order_by(AuditEvent.created_at.desc())
    )
    assert lock_event is not None
    assert lock_event.actor_id is None
    assert lock_event.safe_metadata is not None
    assert lock_event.safe_metadata["denied_permission_code"] == "roles.view"

    # A subsequent request is now rejected for being locked, not for lacking
    # the permission — get_current_staff_user's account-status check runs
    # before require_permission's own check.
    response = await authed_client.get(_DENIED_PATH, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["message"] == "This account does not have active access."


async def test_denial_lock_threshold_and_window_are_documented_constants() -> None:
    assert _PERMISSION_DENIAL_LIMIT == 10
    assert _PERMISSION_DENIAL_WINDOW_SECONDS == 300
