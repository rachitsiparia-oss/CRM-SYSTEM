"""HTTP-layer permission tests for the referrals router —
`referrals.view` / `referrals.manage` / `referrals.review` / `referrals.adjust`.

Business-rule correctness (anti-abuse, reward posting) is covered by
`test_referrals_service.py`; this file checks only the router's own
responsibility: which permission code gates which endpoint. Where no seeded
system role holds exactly one of these four codes in isolation, a scoped
test-only role is built directly against the permission tables (same
technique `tests/test_staff_models.py` already uses) so each permission is
verified on its own, not bundled with a broader role's other grants.
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from app.db.models import (
    Customer,
    Order,
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
    invalidate_permissions_cache(staff_user.id)
    return staff_user


async def _make_customer(session: AsyncSession) -> Customer:
    suffix = uuid.uuid4().hex[:10]
    customer = Customer(
        id=uuid.uuid4(),
        customer_number=f"CUST-{suffix}",
        display_name="Test Customer",
        first_name="Test",
        last_name="Customer",
    )
    session.add(customer)
    await session.flush()
    return customer


def _program_payload(**overrides: Any) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "code": f"ref-{suffix}",
        "name": "Test Referral Program",
        "referrer_reward_amount": 100,
        "referee_reward_amount": 50,
    }
    payload.update(overrides)
    return payload


async def _create_active_program(
    authed_client: AsyncClient, owner: StaffUser, **overrides: Any
) -> dict[str, Any]:
    create_response = await authed_client.post(
        "/api/v1/referrals/programs", json=_program_payload(**overrides), headers=_headers(owner)
    )
    assert create_response.status_code == 201, create_response.text
    program = create_response.json()["data"]
    transition_response = await authed_client.post(
        f"/api/v1/referrals/programs/{program['id']}/transition",
        json={"target_status": "active"},
        headers=_headers(owner),
    )
    assert transition_response.status_code == 200, transition_response.text
    data: dict[str, Any] = transition_response.json()["data"]
    return data


# --- referrals.view -----------------------------------------------------


async def test_list_programs_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/referrals/programs")
    assert response.status_code == 401


async def test_list_programs_requires_referrals_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/referrals/programs", headers=_headers(outsider))
    assert response.status_code == 403


async def test_list_programs_succeeds_with_referrals_view_only(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    viewer = await _make_scoped_staff_user(
        db_session, make_staff_user, permission_codes=("referrals.view",)
    )
    response = await authed_client.get("/api/v1/referrals/programs", headers=_headers(viewer))
    assert response.status_code == 200


# --- referrals.manage -----------------------------------------------------


async def test_create_program_requires_referrals_manage_not_just_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    viewer = await _make_scoped_staff_user(
        db_session, make_staff_user, permission_codes=("referrals.view",)
    )
    response = await authed_client.post(
        "/api/v1/referrals/programs", json=_program_payload(), headers=_headers(viewer)
    )
    assert response.status_code == 403


async def test_create_program_succeeds_with_referrals_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    manager = await _make_scoped_staff_user(
        db_session, make_staff_user, permission_codes=("referrals.manage",)
    )
    response = await authed_client.post(
        "/api/v1/referrals/programs", json=_program_payload(), headers=_headers(manager)
    )
    assert response.status_code == 201, response.text


async def test_issue_code_and_attribute_require_referrals_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    program = await _create_active_program(authed_client, owner)
    referrer = await _make_customer(db_session)

    viewer = await _make_scoped_staff_user(
        db_session, make_staff_user, permission_codes=("referrals.view",)
    )
    response = await authed_client.post(
        f"/api/v1/referrals/programs/{program['id']}/codes",
        json={"referrer_customer_id": str(referrer.id)},
        headers=_headers(viewer),
    )
    assert response.status_code == 403


# --- referrals.review -----------------------------------------------------


async def test_reject_relationship_requires_referrals_review_not_just_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    program = await _create_active_program(authed_client, owner)
    referrer = await _make_customer(db_session)

    code_response = await authed_client.post(
        f"/api/v1/referrals/programs/{program['id']}/codes",
        json={"referrer_customer_id": str(referrer.id)},
        headers=_headers(owner),
    )
    assert code_response.status_code == 201, code_response.text
    code_value = code_response.json()["data"]["code"]

    attribute_response = await authed_client.post(
        "/api/v1/referrals/relationships/attribute",
        json={"code": code_value, "referred_contact": "9876500001"},
        headers=_headers(owner),
    )
    assert attribute_response.status_code == 201, attribute_response.text
    relationship_id = attribute_response.json()["data"]["id"]

    manage_only = await _make_scoped_staff_user(
        db_session, make_staff_user, permission_codes=("referrals.manage",)
    )
    response = await authed_client.post(
        f"/api/v1/referrals/relationships/{relationship_id}/reject",
        json={"reason": "test"},
        headers=_headers(manage_only),
    )
    assert response.status_code == 403


async def test_reject_relationship_succeeds_with_referrals_review(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    program = await _create_active_program(authed_client, owner)
    referrer = await _make_customer(db_session)

    code_response = await authed_client.post(
        f"/api/v1/referrals/programs/{program['id']}/codes",
        json={"referrer_customer_id": str(referrer.id)},
        headers=_headers(owner),
    )
    code_value = code_response.json()["data"]["code"]
    attribute_response = await authed_client.post(
        "/api/v1/referrals/relationships/attribute",
        json={"code": code_value, "referred_contact": "9876500002"},
        headers=_headers(owner),
    )
    relationship_id = attribute_response.json()["data"]["id"]

    reviewer = await _make_scoped_staff_user(
        db_session, make_staff_user, permission_codes=("referrals.review",)
    )
    response = await authed_client.post(
        f"/api/v1/referrals/relationships/{relationship_id}/reject",
        json={"reason": "test"},
        headers=_headers(reviewer),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "rejected"


# --- referrals.adjust -----------------------------------------------------


async def test_reward_relationship_requires_referrals_adjust_not_just_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    program = await _create_active_program(authed_client, owner, reward_hold_days=0)
    referrer = await _make_customer(db_session)
    referee = await _make_customer(db_session)

    code_response = await authed_client.post(
        f"/api/v1/referrals/programs/{program['id']}/codes",
        json={"referrer_customer_id": str(referrer.id)},
        headers=_headers(owner),
    )
    code_value = code_response.json()["data"]["code"]
    attribute_response = await authed_client.post(
        "/api/v1/referrals/relationships/attribute",
        json={
            "code": code_value,
            "referred_contact": "9876500003",
            "referred_customer_id": str(referee.id),
        },
        headers=_headers(owner),
    )
    relationship_id = attribute_response.json()["data"]["id"]

    order_id = uuid.uuid4()
    # qualifying_order_id is a real FK to orders.id — insert a bare order row
    # directly so it is satisfiable, matching test_referrals_service.py's own
    # minimal Order helper.
    db_session.add(
        Order(
            id=order_id,
            order_number=f"ORD-{uuid.uuid4().hex[:10]}",
            source="manual",
            order_type="takeaway",
            status="draft",
            payment_status="pending",
        )
    )
    await db_session.flush()

    qualify_response = await authed_client.post(
        f"/api/v1/referrals/relationships/{relationship_id}/qualify",
        json={"qualifying_order_id": str(order_id)},
        headers=_headers(owner),
    )
    assert qualify_response.status_code == 200, qualify_response.text

    manage_only = await _make_scoped_staff_user(
        db_session, make_staff_user, permission_codes=("referrals.manage",)
    )
    response = await authed_client.post(
        f"/api/v1/referrals/relationships/{relationship_id}/reward",
        headers=_headers(manage_only),
    )
    assert response.status_code == 403
