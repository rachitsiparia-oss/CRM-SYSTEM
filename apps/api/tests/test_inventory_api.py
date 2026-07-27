"""HTTP-layer tests for the inventory router — authentication,
authorization, and optimistic concurrency. Business-rule correctness
(ledger math, receipts, recipes, order integration) is covered by the other
`test_inventory_*.py` files; this file checks the router's own
responsibilities: permission enforcement and version-conflict handling.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests._inventory_helpers import make_category, make_unit
from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


def _unit_payload(**overrides: Any) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "code": f"unit-{suffix}",
        "name": f"Unit {suffix}",
        "symbol": suffix[:6],
        "unit_type": "count",
        "conversion_factor": "1",
        "decimal_places": 0,
    }
    payload.update(overrides)
    return payload


def _item_payload(
    *, category_id: uuid.UUID, base_unit_id: uuid.UUID, **overrides: Any
) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "name": f"Item {suffix}",
        "category_id": str(category_id),
        "base_unit_id": str(base_unit_id),
    }
    payload.update(overrides)
    return payload


# --- Authentication and authorization ----------------------------------------


async def test_list_units_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/inventory/units")
    assert response.status_code == 401


async def test_list_units_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)  # no role, no permissions at all
    response = await authed_client.get("/api/v1/inventory/units", headers=_headers(outsider))
    assert response.status_code == 403


async def test_create_unit_requires_units_manage_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # kitchen_staff has inventory.view but not inventory.units.manage.
    staff = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        "/api/v1/inventory/units", json=_unit_payload(), headers=_headers(staff)
    )
    assert response.status_code == 403


async def test_create_unit_succeeds_for_owner(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    response = await authed_client.post(
        "/api/v1/inventory/units", json=_unit_payload(), headers=_headers(owner)
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["version"] == 1


async def test_balances_rebuild_requires_dedicated_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # inventory_manager has broad day-to-day CRUD but explicitly NOT
    # inventory.balances.rebuild (see role_matrix.py's own documented split).
    inventory_manager = await make_staff_user(role_code="inventory_manager")
    response = await authed_client.post(
        "/api/v1/inventory/balances/rebuild", headers=_headers(inventory_manager)
    )
    assert response.status_code == 403


async def test_balances_rebuild_succeeds_for_owner(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    response = await authed_client.post(
        "/api/v1/inventory/balances/rebuild", headers=_headers(owner)
    )
    assert response.status_code == 200, response.text


# --- CRUD and optimistic concurrency ----------------------------------------


async def test_create_and_get_inventory_item(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    category = await make_category(db_session)
    unit = await make_unit(db_session, unit_type="count", decimal_places=0)

    response = await authed_client.post(
        "/api/v1/inventory/items",
        json=_item_payload(category_id=category.id, base_unit_id=unit.id),
        headers=_headers(owner),
    )
    assert response.status_code == 201, response.text
    item_id = response.json()["data"]["id"]

    get_response = await authed_client.get(
        f"/api/v1/inventory/items/{item_id}", headers=_headers(owner)
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == item_id


async def test_update_item_with_stale_version_returns_409(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    category = await make_category(db_session)
    unit = await make_unit(db_session, unit_type="count", decimal_places=0)

    create_response = await authed_client.post(
        "/api/v1/inventory/items",
        json=_item_payload(category_id=category.id, base_unit_id=unit.id),
        headers=_headers(owner),
    )
    item_id = create_response.json()["data"]["id"]

    # First update succeeds and bumps the version.
    ok_response = await authed_client.patch(
        f"/api/v1/inventory/items/{item_id}",
        json={"name": "Renamed once", "expected_version": 1},
        headers=_headers(owner),
    )
    assert ok_response.status_code == 200, ok_response.text

    # Retrying with the now-stale version must be rejected, not silently
    # overwrite the intervening change.
    stale_response = await authed_client.patch(
        f"/api/v1/inventory/items/{item_id}",
        json={"name": "Renamed twice", "expected_version": 1},
        headers=_headers(owner),
    )
    assert stale_response.status_code == 409


async def test_get_unknown_item_returns_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get(
        f"/api/v1/inventory/items/{uuid.uuid4()}", headers=_headers(owner)
    )
    assert response.status_code == 404
