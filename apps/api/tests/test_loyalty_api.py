"""HTTP-layer tests for the loyalty router — authentication and
authorization. Ledger/account/tier correctness is covered by
`test_loyalty_ledger.py`; this file checks the router's own
responsibilities: permission enforcement per endpoint.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import Customer, StaffUser
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _make_customer(session: AsyncSession, **overrides: object) -> Customer:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": f"Customer {suffix}",
        "first_name": "Test",
        "last_name": "Customer",
    }
    fields.update(overrides)
    customer = Customer(**fields)
    session.add(customer)
    await session.flush()
    return customer


def _program_payload(**overrides: Any) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {"code": f"program-{suffix}", "name": f"Program {suffix}"}
    payload.update(overrides)
    return payload


async def _setup_active_account(
    authed_client: AsyncClient, owner: StaffUser, session: AsyncSession
) -> tuple[str, str]:
    """Creates an active program and an enrolled account, all as `owner`
    (who has every permission). Returns (account_id, program_id)."""
    create_resp = await authed_client.post(
        "/api/v1/loyalty/programs", json=_program_payload(), headers=_headers(owner)
    )
    assert create_resp.status_code == 201, create_resp.text
    program_id = create_resp.json()["data"]["id"]

    transition_resp = await authed_client.post(
        f"/api/v1/loyalty/programs/{program_id}/transition",
        json={"target_status": "active"},
        headers=_headers(owner),
    )
    assert transition_resp.status_code == 200, transition_resp.text

    customer = await _make_customer(session)
    enroll_resp = await authed_client.post(
        "/api/v1/loyalty/accounts",
        json={"customer_id": str(customer.id), "program_id": program_id},
        headers=_headers(owner),
    )
    assert enroll_resp.status_code == 201, enroll_resp.text
    account_id = enroll_resp.json()["data"]["id"]
    return account_id, program_id


# --- Authentication and authorization ----------------------------------------


async def test_list_programs_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/loyalty/programs")
    assert response.status_code == 401


async def test_list_programs_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/loyalty/programs", headers=_headers(outsider))
    assert response.status_code == 403


async def test_create_program_requires_loyalty_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # operations_manager has loyalty.view but not loyalty.manage.
    view_only = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/loyalty/programs", json=_program_payload(), headers=_headers(view_only)
    )
    assert response.status_code == 403


async def test_create_program_succeeds_for_loyalty_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # marketing_manager owns loyalty program design.
    manager = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/loyalty/programs", json=_program_payload(), headers=_headers(manager)
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["status"] == "draft"


async def test_earn_requires_loyalty_adjust(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id, _program_id = await _setup_active_account(authed_client, owner, db_session)

    view_only = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/loyalty/earn",
        json={
            "account_id": account_id,
            "entry_type": "earn_manual",
            "points": 10,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(view_only),
    )
    assert response.status_code == 403


async def test_earn_succeeds_for_loyalty_adjust(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id, _program_id = await _setup_active_account(authed_client, owner, db_session)

    # marketing_manager has loyalty.adjust for service-recovery-style earns.
    adjuster = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/loyalty/earn",
        json={
            "account_id": account_id,
            "entry_type": "earn_manual",
            "points": 10,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(adjuster),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["points_delta"] == 10


async def test_redeem_requires_loyalty_adjust(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id, _program_id = await _setup_active_account(authed_client, owner, db_session)
    await authed_client.post(
        "/api/v1/loyalty/earn",
        json={
            "account_id": account_id,
            "entry_type": "earn_manual",
            "points": 50,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(owner),
    )

    view_only = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/loyalty/redeem",
        json={
            "account_id": account_id,
            "points": 10,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(view_only),
    )
    assert response.status_code == 403


async def test_redeem_succeeds_for_loyalty_adjust(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id, _program_id = await _setup_active_account(authed_client, owner, db_session)
    await authed_client.post(
        "/api/v1/loyalty/earn",
        json={
            "account_id": account_id,
            "entry_type": "earn_manual",
            "points": 50,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(owner),
    )

    adjuster = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/loyalty/redeem",
        json={
            "account_id": account_id,
            "points": 10,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(adjuster),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["points_delta"] == -10


async def test_analytics_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    view_only = await make_staff_user(role_code="operations_manager")
    response = await authed_client.get("/api/v1/loyalty/analytics", headers=_headers(view_only))
    assert response.status_code == 403

    analyst = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.get("/api/v1/loyalty/analytics", headers=_headers(analyst))
    assert response.status_code == 200
