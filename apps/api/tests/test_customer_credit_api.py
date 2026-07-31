"""HTTP-layer tests for the customer-credit router — authentication and
authorization. Ledger correctness is covered by
`test_customer_credit_ledger.py`; this file checks the router's own
responsibility: permission enforcement per endpoint.
"""

import uuid
from collections.abc import Awaitable, Callable

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


async def _setup_account(
    authed_client: AsyncClient, issuer: StaffUser, session: AsyncSession
) -> str:
    customer = await _make_customer(session)
    response = await authed_client.post(
        "/api/v1/customer-credit/accounts",
        json={"customer_id": str(customer.id)},
        headers=_headers(issuer),
    )
    assert response.status_code == 201, response.text
    account_id: str = response.json()["data"]["id"]
    return account_id


# --- Authentication and authorization ----------------------------------------


async def test_get_account_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get(
        f"/api/v1/customer-credit/accounts?customer_id={uuid.uuid4()}"
    )
    assert response.status_code == 401


async def test_get_account_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get(
        f"/api/v1/customer-credit/accounts?customer_id={uuid.uuid4()}",
        headers=_headers(outsider),
    )
    assert response.status_code == 403


async def test_issue_requires_customer_credit_issue(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    issuer = await make_staff_user(role_code="finance_manager")
    account_id = await _setup_account(authed_client, issuer, db_session)

    # operations_manager only has customer_credit.view.
    view_only = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/customer-credit/issue",
        json={
            "account_id": account_id,
            "amount_minor": 1000,
            "issue_reason": "service_recovery",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(view_only),
    )
    assert response.status_code == 403


async def test_issue_succeeds_for_customer_support_agent(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id = await _setup_account(authed_client, owner, db_session)

    # customer_support_agent has customer_credit.issue for small
    # service-recovery credits.
    agent = await make_staff_user(role_code="customer_support_agent")
    response = await authed_client.post(
        "/api/v1/customer-credit/issue",
        json={
            "account_id": account_id,
            "amount_minor": 500,
            "issue_reason": "service_recovery",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(agent),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["amount_delta_minor"] == 500


async def test_adjust_requires_customer_credit_adjust(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id = await _setup_account(authed_client, owner, db_session)

    # marketing_manager has customer_credit.view but not .adjust.
    view_only = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/customer-credit/adjust",
        json={
            "account_id": account_id,
            "amount_delta_minor": 200,
            "reason": "goodwill",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(view_only),
    )
    assert response.status_code == 403


async def test_adjust_succeeds_for_finance_manager(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id = await _setup_account(authed_client, owner, db_session)

    finance = await make_staff_user(role_code="finance_manager")
    response = await authed_client.post(
        "/api/v1/customer-credit/adjust",
        json={
            "account_id": account_id,
            "amount_delta_minor": 200,
            "reason": "goodwill",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(finance),
    )
    assert response.status_code == 201, response.text


async def test_reverse_requires_customer_credit_reverse(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id = await _setup_account(authed_client, owner, db_session)
    issue_resp = await authed_client.post(
        "/api/v1/customer-credit/issue",
        json={
            "account_id": account_id,
            "amount_minor": 500,
            "issue_reason": "service_recovery",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(owner),
    )
    entry_id = issue_resp.json()["data"]["id"]

    # finance_manager has customer_credit.adjust but reverse is only tested
    # for absence on a role with neither: operations_manager.
    view_only = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/customer-credit/reverse",
        json={
            "entry_id": entry_id,
            "reason": "mistake",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(view_only),
    )
    assert response.status_code == 403


async def test_reverse_succeeds_for_finance_manager(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    account_id = await _setup_account(authed_client, owner, db_session)
    issue_resp = await authed_client.post(
        "/api/v1/customer-credit/issue",
        json={
            "account_id": account_id,
            "amount_minor": 500,
            "issue_reason": "service_recovery",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(owner),
    )
    entry_id = issue_resp.json()["data"]["id"]

    finance = await make_staff_user(role_code="finance_manager")
    response = await authed_client.post(
        "/api/v1/customer-credit/reverse",
        json={
            "entry_id": entry_id,
            "reason": "mistake",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(finance),
    )
    assert response.status_code == 201, response.text


async def test_analytics_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get(
        "/api/v1/customer-credit/analytics", headers=_headers(outsider)
    )
    assert response.status_code == 403

    analyst = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.get(
        "/api/v1/customer-credit/analytics", headers=_headers(analyst)
    )
    assert response.status_code == 200
