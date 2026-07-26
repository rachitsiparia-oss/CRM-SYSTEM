import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import MenuCategory, Modifier, Product, ProductVariant, StaffUser
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _make_product(
    session: AsyncSession, *, price_minor: int = 19900, **overrides: object
) -> Product:
    suffix = uuid.uuid4().hex[:10]
    category = MenuCategory(id=uuid.uuid4(), code=f"cat-{suffix}", name="Test Category")
    session.add(category)
    await session.flush()

    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "product_code": f"PROD-{suffix}",
        "category_id": category.id,
        "name": "Test Product",
        "slug": f"test-product-{suffix}",
        "food_type": "vegetarian",
        "base_price_minor": price_minor,
    }
    fields.update(overrides)
    product = Product(**fields)
    session.add(product)
    await session.flush()
    return product


async def _make_variant(
    session: AsyncSession, product: Product, *, price_minor: int
) -> ProductVariant:
    suffix = uuid.uuid4().hex[:10]
    variant = ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        code=f"VAR-{suffix}",
        name="Large",
        price_minor=price_minor,
    )
    session.add(variant)
    await session.flush()
    return variant


async def _make_modifier(session: AsyncSession, *, price_minor: int = 3500) -> Modifier:
    suffix = uuid.uuid4().hex[:10]
    modifier = Modifier(id=uuid.uuid4(), name=f"Add-on {suffix}", default_price_minor=price_minor)
    session.add(modifier)
    await session.flush()
    return modifier


def _item_payload(product_id: Any, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"product_id": str(product_id), "quantity": 1}
    payload.update(overrides)
    return payload


def _order_payload(items: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": "manual",
        "order_type": "takeaway",
        "items": items,
        "idempotency_key": f"test-{uuid.uuid4().hex}",
    }
    payload.update(overrides)
    return payload


async def _create_order(
    authed_client: AsyncClient, staff_user: StaffUser, items: list[dict[str, Any]], **overrides: Any
) -> dict[str, Any]:
    response = await authed_client.post(
        "/api/v1/orders",
        json=_order_payload(items, **overrides),
        headers=_headers(staff_user),
    )
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


# --- Authentication and authorization ----------------------------------------


async def test_list_orders_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/orders")
    assert response.status_code == 401


async def test_create_order_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    product = await _make_product(db_session)
    response = await authed_client.post(
        "/api/v1/orders",
        json=_order_payload([_item_payload(product.id)]),
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


async def test_get_order_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    outsider = await make_staff_user(role_code="hr_manager")
    response = await authed_client.get(f"/api/v1/orders/{order['id']}", headers=_headers(outsider))
    assert response.status_code == 403


# --- Creation, pricing, idempotency -------------------------------------------


async def test_create_order_computes_totals_server_side(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session, price_minor=10000)
    modifier = await _make_modifier(db_session, price_minor=2000)

    order = await _create_order(
        authed_client,
        staff_user,
        [
            _item_payload(
                product.id,
                quantity=2,
                modifiers=[{"modifier_id": str(modifier.id), "quantity": 1}],
            )
        ],
    )
    # (unit_price 10000 + modifier 2000) * quantity 2 == 24000
    assert order["subtotal_minor"] == 24000
    assert order["grand_total_minor"] == 24000
    assert order["items"][0]["unit_price_minor"] == 10000
    assert order["items"][0]["final_price_minor"] == 24000
    assert order["items"][0]["modifiers"][0]["price_minor_snapshot"] == 2000


async def test_create_order_prices_variant_over_base_product(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session, price_minor=10000)
    variant = await _make_variant(db_session, product, price_minor=15000)

    order = await _create_order(
        authed_client, staff_user, [_item_payload(product.id, variant_id=str(variant.id))]
    )
    assert order["items"][0]["unit_price_minor"] == 15000
    assert order["subtotal_minor"] == 15000


async def test_create_order_rejects_unknown_product(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    response = await authed_client.post(
        "/api/v1/orders",
        json=_order_payload([_item_payload(uuid.uuid4())]),
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_create_order_applies_discount_tax_and_charges(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session, price_minor=10000)

    order = await _create_order(
        authed_client,
        staff_user,
        [_item_payload(product.id, quantity=1)],
        discounts=[
            {
                "discount_type": "flat",
                "amount_minor": 1000,
                "reason": "Loyalty discount",
                "approved_by": str(staff_user.id),
            }
        ],
        taxes=[{"tax_name": "GST", "rate_percentage": 5}],
        charges=[{"charge_type": "packaging", "amount_minor": 500}],
    )
    # subtotal 10000, discount 1000 -> taxable base 9000, tax 5% -> 450, charges 500
    assert order["subtotal_minor"] == 10000
    assert order["discount_minor"] == 1000
    assert order["tax_minor"] == 450
    assert order["charges_minor"] == 500
    assert order["grand_total_minor"] == 10000 - 1000 + 450 + 500


async def test_create_order_discount_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="front_of_house_staff")
    product = await _make_product(db_session, price_minor=10000)
    response = await authed_client.post(
        "/api/v1/orders",
        json=_order_payload(
            [_item_payload(product.id)],
            discounts=[
                {
                    "discount_type": "manager_override",
                    "amount_minor": 1000,
                    "reason": "test",
                    "approved_by": str(staff_user.id),
                }
            ],
        ),
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


async def test_create_order_is_idempotent(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    key = f"idem-{uuid.uuid4().hex}"

    first = await authed_client.post(
        "/api/v1/orders",
        json=_order_payload([_item_payload(product.id)], idempotency_key=key),
        headers=_headers(staff_user),
    )
    second = await authed_client.post(
        "/api/v1/orders",
        json=_order_payload([_item_payload(product.id)], idempotency_key=key),
        headers=_headers(staff_user),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


# --- Update / optimistic concurrency -------------------------------------------


async def test_update_order_version_conflict_returns_409(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, staff_user, [_item_payload(product.id)])

    response = await authed_client.patch(
        f"/api/v1/orders/{order['id']}",
        json={"internal_notes": "stale write", "expected_version": order["version"] + 1},
        headers=_headers(staff_user),
    )
    assert response.status_code == 409


async def test_update_order_blocked_once_completed(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, staff_user, [_item_payload(product.id)])

    for target in ("pending_confirmation", "confirmed", "preparing", "ready", "completed"):
        response = await authed_client.post(
            f"/api/v1/orders/{order['id']}/transition",
            json={"new_status": target},
            headers=_headers(staff_user),
        )
        assert response.status_code == 200, response.text

    response = await authed_client.patch(
        f"/api/v1/orders/{order['id']}",
        json={"internal_notes": "too late"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


# --- Status transitions ---------------------------------------------------------


async def test_transition_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, staff_user, [_item_payload(product.id)])

    for target in ("pending_confirmation", "confirmed", "preparing", "ready", "completed"):
        response = await authed_client.post(
            f"/api/v1/orders/{order['id']}/transition",
            json={"new_status": target},
            headers=_headers(staff_user),
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["status"] == target


async def test_transition_rejects_skipping_steps(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, staff_user, [_item_payload(product.id)])

    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/transition",
        json={"new_status": "confirmed"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_transition_rejects_cancel_from_confirmed(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, staff_user, [_item_payload(product.id)])

    for target in ("pending_confirmation", "confirmed"):
        response = await authed_client.post(
            f"/api/v1/orders/{order['id']}/transition",
            json={"new_status": target},
            headers=_headers(staff_user),
        )
        assert response.status_code == 200

    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/transition",
        json={"new_status": "cancelled"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_transition_cancel_requires_orders_cancel_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])
    await authed_client.post(
        f"/api/v1/orders/{order['id']}/transition",
        json={"new_status": "pending_confirmation"},
        headers=_headers(owner),
    )

    # kitchen_staff has orders.transition but neither orders.cancel nor
    # orders.complete — exercises the service-level permission check that
    # sits below the router-level orders.transition dependency.
    limited = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/transition",
        json={"new_status": "cancelled"},
        headers=_headers(limited),
    )
    assert response.status_code == 403


async def test_transition_complete_requires_orders_complete_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])
    for target in ("pending_confirmation", "confirmed", "preparing", "ready"):
        await authed_client.post(
            f"/api/v1/orders/{order['id']}/transition",
            json={"new_status": target},
            headers=_headers(owner),
        )

    limited = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/transition",
        json={"new_status": "completed"},
        headers=_headers(limited),
    )
    assert response.status_code == 403


# --- Assignment -----------------------------------------------------------------


async def test_assign_order_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    limited = await make_staff_user(role_code="hr_manager")
    target_staff = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/assign",
        json={"assigned_staff_id": str(target_staff.id)},
        headers=_headers(limited),
    )
    assert response.status_code == 403


async def test_assign_order_success(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    target_staff = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/assign",
        json={"assigned_staff_id": str(target_staff.id)},
        headers=_headers(owner),
    )
    assert response.status_code == 200
    assert response.json()["data"]["assigned_staff_id"] == str(target_staff.id)


# --- Payments --------------------------------------------------------------------


async def test_add_payment_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session, price_minor=10000)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    limited = await make_staff_user(role_code="hr_manager")
    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/payments",
        json={"method": "cash", "status": "paid", "amount_minor": 10000},
        headers=_headers(limited),
    )
    assert response.status_code == 403


async def test_add_partial_payment_updates_order_payment_status(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session, price_minor=10000)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/payments",
        json={"method": "cash", "status": "paid", "amount_minor": 5000},
        headers=_headers(owner),
    )
    assert response.status_code == 201

    get_response = await authed_client.get(f"/api/v1/orders/{order['id']}", headers=_headers(owner))
    assert get_response.json()["data"]["payment_status"] == "partial"


async def test_add_full_payment_marks_order_paid(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session, price_minor=10000)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    await authed_client.post(
        f"/api/v1/orders/{order['id']}/payments",
        json={"method": "upi", "status": "paid", "amount_minor": 10000},
        headers=_headers(owner),
    )
    get_response = await authed_client.get(f"/api/v1/orders/{order['id']}", headers=_headers(owner))
    assert get_response.json()["data"]["payment_status"] == "paid"


async def test_update_payment_status_to_refunded(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session, price_minor=10000)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    payment_response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/payments",
        json={"method": "upi", "status": "paid", "amount_minor": 10000},
        headers=_headers(owner),
    )
    payment_id = payment_response.json()["data"]["id"]

    response = await authed_client.patch(
        f"/api/v1/orders/{order['id']}/payments/{payment_id}",
        json={"status": "refunded"},
        headers=_headers(owner),
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "refunded"

    get_response = await authed_client.get(f"/api/v1/orders/{order['id']}", headers=_headers(owner))
    assert get_response.json()["data"]["payment_status"] == "refunded"


# --- Notes -------------------------------------------------------------------------


async def test_add_note_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    limited = await make_staff_user(role_code="hr_manager")
    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/notes",
        json={"content": "test note"},
        headers=_headers(limited),
    )
    assert response.status_code == 403


async def test_add_and_list_notes(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    response = await authed_client.post(
        f"/api/v1/orders/{order['id']}/notes",
        json={"content": "Customer asked for extra napkins.", "is_internal": True},
        headers=_headers(owner),
    )
    assert response.status_code == 201

    list_response = await authed_client.get(
        f"/api/v1/orders/{order['id']}/notes", headers=_headers(owner)
    )
    assert len(list_response.json()["data"]) == 1


# --- Listing, filtering, timeline ---------------------------------------------


async def test_list_orders_filters_by_status(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    response = await authed_client.get(
        "/api/v1/orders", params={"order_status": "draft"}, headers=_headers(owner)
    )
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()["data"]]
    assert order["id"] in ids


async def test_list_orders_search_by_order_number(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    response = await authed_client.get(
        "/api/v1/orders",
        params={"search": order["order_number"]},
        headers=_headers(owner),
    )
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()["data"]]
    assert order["id"] in ids


async def test_dashboard_stats_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    response = await authed_client.get(
        "/api/v1/orders/dashboard/stats", headers=_headers(staff_user)
    )
    assert response.status_code == 403


async def test_dashboard_stats_counts_todays_orders(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session, price_minor=10000)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])
    for target in ("pending_confirmation", "confirmed", "preparing", "ready", "completed"):
        await authed_client.post(
            f"/api/v1/orders/{order['id']}/transition",
            json={"new_status": target},
            headers=_headers(owner),
        )

    response = await authed_client.get("/api/v1/orders/dashboard/stats", headers=_headers(owner))
    assert response.status_code == 200
    stats = response.json()["data"]
    assert stats["today_order_count"] >= 1
    assert stats["status_counts_today"]["completed"] >= 1
    assert stats["revenue_today_minor"] >= 10000
    assert len(stats["recent_activity"]) > 0


async def test_get_order_timeline_records_created_event(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])

    response = await authed_client.get(
        f"/api/v1/orders/{order['id']}/timeline", headers=_headers(owner)
    )
    assert response.status_code == 200
    event_types = [row["event_type"] for row in response.json()["data"]]
    assert "created" in event_types


async def test_get_order_status_history(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _create_order(authed_client, owner, [_item_payload(product.id)])
    await authed_client.post(
        f"/api/v1/orders/{order['id']}/transition",
        json={"new_status": "pending_confirmation"},
        headers=_headers(owner),
    )

    response = await authed_client.get(
        f"/api/v1/orders/{order['id']}/status-history", headers=_headers(owner)
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
