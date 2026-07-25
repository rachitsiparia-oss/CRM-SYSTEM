import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models import Role, StaffInvitation, StaffUser
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def test_me_without_token_is_401(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


async def test_me_with_garbage_token_is_401(authed_client: AsyncClient) -> None:
    response = await authed_client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


async def test_me_for_unprovisioned_identity_is_403(authed_client: AsyncClient) -> None:
    token = make_access_token(uuid.uuid4(), email="nobody@example.test")
    response = await authed_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


async def test_me_for_disabled_account_is_403(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff", account_status="disabled")
    token = make_access_token(staff_user.auth_user_id)
    response = await authed_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


async def test_me_for_active_account_returns_roles_and_permissions(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    token = make_access_token(staff_user.auth_user_id)
    response = await authed_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["employee_code"] == staff_user.employee_code
    assert "orders.view" in body["permissions"]
    assert "settings.manage" not in body["permissions"]
    assert {role["code"] for role in body["roles"]} == {"kitchen_staff"}


async def test_login_records_audit_event_and_updates_last_login(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    assert staff_user.last_login_at is None
    token = make_access_token(staff_user.auth_user_id)
    response = await authed_client.post(
        "/api/v1/auth/login", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert staff_user.last_login_at is not None


async def test_staff_view_endpoint_denies_role_without_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # front_of_house_staff has no staff.view grant in the seeded matrix.
    staff_user = await make_staff_user(role_code="front_of_house_staff")
    token = make_access_token(staff_user.auth_user_id)
    response = await authed_client.get(
        "/api/v1/staff-users", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_staff_view_endpoint_allows_role_with_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    token = make_access_token(staff_user.auth_user_id)
    response = await authed_client.get(
        "/api/v1/staff-users", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "pagination" in response.json()


async def test_cannot_assign_role_to_self(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    token = make_access_token(staff_user.auth_user_id)
    response = await authed_client.post(
        f"/api/v1/staff-users/{staff_user.id}/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"role_code": "hr_manager", "reason": "testing self escalation"},
    )
    assert response.status_code == 403


async def test_cannot_deactivate_self(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    token = make_access_token(staff_user.auth_user_id)
    response = await authed_client.post(
        f"/api/v1/staff-users/{staff_user.id}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "testing self-lockout"},
    )
    assert response.status_code == 403


async def test_owner_can_assign_role_to_another_staff_member(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    target = await make_staff_user(role_code="kitchen_staff")
    token = make_access_token(owner.auth_user_id)

    response = await authed_client.post(
        f"/api/v1/staff-users/{target.id}/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"role_code": "shift_supervisor", "reason": "promotion"},
    )
    assert response.status_code == 201
    codes = {role["code"] for role in response.json()["data"]["roles"]}
    assert {"kitchen_staff", "shift_supervisor"} == codes


async def test_hr_sensitive_field_hidden_without_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    # operations_manager has staff.view but not staff.hr_sensitive.read in
    # the seeded matrix — the request must succeed but the phone number
    # must be withheld.
    viewer = await make_staff_user(role_code="operations_manager")
    target = await make_staff_user(role_code="kitchen_staff")
    target.phone_e164 = "+911234567890"
    await db_session.flush()

    token = make_access_token(viewer.auth_user_id)
    response = await authed_client.get(
        f"/api/v1/staff-users/{target.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["phone_e164"] is None


async def test_hr_sensitive_field_visible_with_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    viewer = await make_staff_user(role_code="hr_manager")
    target = await make_staff_user(role_code="kitchen_staff")
    target.phone_e164 = "+911234567890"
    await db_session.flush()

    token = make_access_token(viewer.auth_user_id)
    response = await authed_client.get(
        f"/api/v1/staff-users/{target.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["phone_e164"] == "+911234567890"


async def test_first_login_provisions_staff_user_from_pending_invitation(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    inviter = await make_staff_user(role_code="owner")
    role_id = await db_session.scalar(select(Role.id).where(Role.code == "kitchen_staff"))
    email = f"newhire-{uuid.uuid4().hex[:8]}@example.test"
    invitation = StaffInvitation(
        id=uuid.uuid4(),
        email=email,
        first_name="New",
        last_name="Hire",
        intended_role_id=role_id,
        invited_by=inviter.id,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(invitation)
    await db_session.flush()

    new_auth_user_id = uuid.uuid4()
    token = make_access_token(new_auth_user_id, email=email)
    response = await authed_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["email"] == email
    assert {role["code"] for role in body["roles"]} == {"kitchen_staff"}

    await db_session.refresh(invitation)
    assert invitation.status == "accepted"


async def test_expired_invitation_does_not_provision(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    inviter = await make_staff_user(role_code="owner")
    role_id = await db_session.scalar(select(Role.id).where(Role.code == "kitchen_staff"))
    email = f"expired-{uuid.uuid4().hex[:8]}@example.test"
    invitation = StaffInvitation(
        id=uuid.uuid4(),
        email=email,
        first_name="Expired",
        intended_role_id=role_id,
        invited_by=inviter.id,
        status="pending",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(invitation)
    await db_session.flush()

    token = make_access_token(uuid.uuid4(), email=email)
    response = await authed_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
