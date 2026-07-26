import io
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient
from PIL import Image

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


def _category_payload(**overrides: Any) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {"code": f"cat-{suffix}", "name": "Test Category"}
    payload.update(overrides)
    return payload


def _product_payload(category_id: Any, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "category_id": category_id,
        "name": "Test Product",
        "food_type": "vegetarian",
        "base_price_minor": 19900,
    }
    payload.update(overrides)
    return payload


def _test_image_bytes(color: tuple[int, int, int] = (200, 50, 50)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=color).save(buf, format="JPEG")
    return buf.getvalue()


async def _create_category(authed_client: AsyncClient, staff_user: StaffUser) -> dict[str, Any]:
    response = await authed_client.post(
        "/api/v1/menu/categories", json=_category_payload(), headers=_headers(staff_user)
    )
    assert response.status_code == 201
    data: dict[str, Any] = response.json()["data"]
    return data


async def _create_product(authed_client: AsyncClient, staff_user: StaffUser) -> dict[str, Any]:
    category = await _create_category(authed_client, staff_user)
    response = await authed_client.post(
        "/api/v1/menu/products",
        json=_product_payload(category["id"]),
        headers=_headers(staff_user),
    )
    assert response.status_code == 201
    data: dict[str, Any] = response.json()["data"]
    return data


# --- Categories -----------------------------------------------------------


async def test_list_categories_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/menu/categories")
    assert response.status_code == 401


async def test_create_category_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        "/api/v1/menu/categories", json=_category_payload(), headers=_headers(staff_user)
    )
    assert response.status_code == 403


async def test_create_and_get_category(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_category(authed_client, staff_user)
    assert created["is_active"] is True

    get_response = await authed_client.get(
        f"/api/v1/menu/categories/{created['id']}", headers=_headers(staff_user)
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == created["id"]


async def test_category_code_conflict(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    payload = _category_payload()
    first = await authed_client.post(
        "/api/v1/menu/categories", json=payload, headers=_headers(staff_user)
    )
    assert first.status_code == 201

    second = await authed_client.post(
        "/api/v1/menu/categories", json=payload, headers=_headers(staff_user)
    )
    assert second.status_code == 409


async def test_update_category_conflicts_on_stale_version(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_category(authed_client, staff_user)

    response = await authed_client.patch(
        f"/api/v1/menu/categories/{created['id']}",
        json={"name": "Renamed", "expected_version": created["version"] + 1},
        headers=_headers(staff_user),
    )
    assert response.status_code == 409


async def test_archive_and_restore_category(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_category(authed_client, staff_user)

    archive_response = await authed_client.request(
        "DELETE",
        f"/api/v1/menu/categories/{created['id']}",
        json={"reason": "Seasonal menu cleanup."},
        headers=_headers(staff_user),
    )
    assert archive_response.status_code == 200

    list_response = await authed_client.get("/api/v1/menu/categories", headers=_headers(staff_user))
    assert created["id"] not in {row["id"] for row in list_response.json()["data"]}

    restore_response = await authed_client.post(
        f"/api/v1/menu/categories/{created['id']}/restore", headers=_headers(staff_user)
    )
    assert restore_response.status_code == 200


async def test_reorder_categories(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    first = await _create_category(authed_client, staff_user)
    second = await _create_category(authed_client, staff_user)

    response = await authed_client.post(
        "/api/v1/menu/categories/reorder",
        json={"ordered_category_ids": [second["id"], first["id"]]},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200

    first_after = await authed_client.get(
        f"/api/v1/menu/categories/{first['id']}", headers=_headers(staff_user)
    )
    second_after = await authed_client.get(
        f"/api/v1/menu/categories/{second['id']}", headers=_headers(staff_user)
    )
    assert second_after.json()["data"]["sort_order"] < first_after.json()["data"]["sort_order"]


# --- Products -----------------------------------------------------------


async def test_create_product_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    manager = await make_staff_user(role_code="kitchen_manager")
    staff = await make_staff_user(role_code="kitchen_staff")
    category = await _create_category(authed_client, manager)

    response = await authed_client.post(
        "/api/v1/menu/products", json=_product_payload(category["id"]), headers=_headers(staff)
    )
    assert response.status_code == 403


async def test_create_product_requires_a_real_category(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    response = await authed_client.post(
        "/api/v1/menu/products",
        json=_product_payload(str(uuid.uuid4())),
        headers=_headers(staff_user),
    )
    assert response.status_code == 404


async def test_create_and_get_product(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_product(authed_client, staff_user)
    assert created["is_active"] is True
    assert created["version"] == 1

    get_response = await authed_client.get(
        f"/api/v1/menu/products/{created['id']}", headers=_headers(staff_user)
    )
    assert get_response.status_code == 200


async def test_update_product_conflicts_on_stale_version(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_product(authed_client, staff_user)

    response = await authed_client.patch(
        f"/api/v1/menu/products/{created['id']}",
        json={"name": "Renamed", "expected_version": created["version"] + 1},
        headers=_headers(staff_user),
    )
    assert response.status_code == 409


async def test_update_product_succeeds(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_product(authed_client, staff_user)

    response = await authed_client.patch(
        f"/api/v1/menu/products/{created['id']}",
        json={"base_price_minor": 22900, "expected_version": created["version"]},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["base_price_minor"] == 22900
    assert body["version"] == created["version"] + 1


async def test_duplicate_product(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_product(authed_client, staff_user)
    await authed_client.post(
        f"/api/v1/menu/products/{created['id']}/variants",
        json={"code": f"var-{uuid.uuid4().hex[:8]}", "name": "Large", "price_minor": 29900},
        headers=_headers(staff_user),
    )

    response = await authed_client.post(
        f"/api/v1/menu/products/{created['id']}/duplicate", headers=_headers(staff_user)
    )
    assert response.status_code == 201
    duplicate = response.json()["data"]
    assert duplicate["id"] != created["id"]
    assert duplicate["is_active"] is False
    assert "(Copy)" in duplicate["name"]

    variants_response = await authed_client.get(
        f"/api/v1/menu/products/{duplicate['id']}/variants", headers=_headers(staff_user)
    )
    assert len(variants_response.json()["data"]) == 1


async def test_availability_override_requires_reason(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_product(authed_client, staff_user)

    missing_reason = await authed_client.post(
        f"/api/v1/menu/products/{created['id']}/availability-override",
        json={"is_available": False},
        headers=_headers(staff_user),
    )
    assert missing_reason.status_code == 422

    with_reason = await authed_client.post(
        f"/api/v1/menu/products/{created['id']}/availability-override",
        json={"is_available": False, "reason": "Out of vegetable patties."},
        headers=_headers(staff_user),
    )
    assert with_reason.status_code == 200
    body = with_reason.json()["data"]
    assert body["is_available"] is False
    assert body["availability_source"] == "override"


async def test_archive_product_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    manager = await make_staff_user(role_code="kitchen_manager")
    staff = await make_staff_user(role_code="kitchen_staff")
    created = await _create_product(authed_client, manager)

    response = await authed_client.request(
        "DELETE",
        f"/api/v1/menu/products/{created['id']}",
        json={"reason": "Should be denied."},
        headers=_headers(staff),
    )
    assert response.status_code == 403


async def test_archive_and_restore_product(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    created = await _create_product(authed_client, staff_user)

    archive_response = await authed_client.request(
        "DELETE",
        f"/api/v1/menu/products/{created['id']}",
        json={"reason": "Discontinued item."},
        headers=_headers(staff_user),
    )
    assert archive_response.status_code == 200

    restore_response = await authed_client.post(
        f"/api/v1/menu/products/{created['id']}/restore", headers=_headers(staff_user)
    )
    assert restore_response.status_code == 200


async def test_reorder_products(authed_client: AsyncClient, make_staff_user: MakeStaffUser) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    category = await _create_category(authed_client, staff_user)
    first = (
        await authed_client.post(
            "/api/v1/menu/products",
            json=_product_payload(category["id"], name="First"),
            headers=_headers(staff_user),
        )
    ).json()["data"]
    second = (
        await authed_client.post(
            "/api/v1/menu/products",
            json=_product_payload(category["id"], name="Second"),
            headers=_headers(staff_user),
        )
    ).json()["data"]

    response = await authed_client.post(
        "/api/v1/menu/products/reorder",
        json={"ordered_product_ids": [second["id"], first["id"]]},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200


async def test_list_products_filters_by_vegetarian(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    category = await _create_category(authed_client, staff_user)
    veg = (
        await authed_client.post(
            "/api/v1/menu/products",
            json=_product_payload(category["id"], name="Veg Item", food_type="vegetarian"),
            headers=_headers(staff_user),
        )
    ).json()["data"]
    await authed_client.post(
        "/api/v1/menu/products",
        json=_product_payload(category["id"], name="Non-Veg Item", food_type="non_vegetarian"),
        headers=_headers(staff_user),
    )

    response = await authed_client.get(
        "/api/v1/menu/products",
        params={"is_vegetarian": True, "category_id": category["id"]},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["data"]}
    assert veg["id"] in ids
    assert all(row["food_type"] == "vegetarian" for row in response.json()["data"])


async def test_list_products_rejects_unknown_sort_column(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    response = await authed_client.get(
        "/api/v1/menu/products", params={"sort": "popularity"}, headers=_headers(staff_user)
    )
    assert response.status_code == 400


# --- Variants -----------------------------------------------------------


async def test_add_update_and_archive_variant(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    product = await _create_product(authed_client, staff_user)

    add_response = await authed_client.post(
        f"/api/v1/menu/products/{product['id']}/variants",
        json={"code": f"var-{uuid.uuid4().hex[:8]}", "name": "Small", "price_minor": 15900},
        headers=_headers(staff_user),
    )
    assert add_response.status_code == 201
    variant = add_response.json()["data"]

    update_response = await authed_client.patch(
        f"/api/v1/menu/products/{product['id']}/variants/{variant['id']}",
        json={"code": variant["code"], "name": "Small", "price_minor": 16900},
        headers=_headers(staff_user),
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["price_minor"] == 16900

    archive_response = await authed_client.delete(
        f"/api/v1/menu/products/{product['id']}/variants/{variant['id']}",
        headers=_headers(staff_user),
    )
    assert archive_response.status_code == 200

    list_response = await authed_client.get(
        f"/api/v1/menu/products/{product['id']}/variants", headers=_headers(staff_user)
    )
    assert list_response.json()["data"] == []


# --- Modifier groups, modifiers, and mappings -------------------------------


async def test_modifier_group_and_modifier_workflow(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")

    group_response = await authed_client.post(
        "/api/v1/menu/modifier-groups",
        json={"name": f"Test Group {uuid.uuid4().hex[:6]}", "min_select": 0, "max_select": 3},
        headers=_headers(staff_user),
    )
    assert group_response.status_code == 201
    group = group_response.json()["data"]

    modifier_response = await authed_client.post(
        "/api/v1/menu/modifiers",
        json={"name": f"Test Modifier {uuid.uuid4().hex[:6]}", "default_price_minor": 3000},
        headers=_headers(staff_user),
    )
    assert modifier_response.status_code == 201
    modifier = modifier_response.json()["data"]

    item_response = await authed_client.post(
        f"/api/v1/menu/modifier-groups/{group['id']}/items",
        json={"modifier_id": modifier["id"]},
        headers=_headers(staff_user),
    )
    assert item_response.status_code == 201

    items_list = await authed_client.get(
        f"/api/v1/menu/modifier-groups/{group['id']}/items", headers=_headers(staff_user)
    )
    assert len(items_list.json()["data"]) == 1

    remove_response = await authed_client.delete(
        f"/api/v1/menu/modifier-groups/{group['id']}/items/{modifier['id']}",
        headers=_headers(staff_user),
    )
    assert remove_response.status_code == 200

    archive_response = await authed_client.delete(
        f"/api/v1/menu/modifier-groups/{group['id']}", headers=_headers(staff_user)
    )
    assert archive_response.status_code == 200

    restore_response = await authed_client.post(
        f"/api/v1/menu/modifier-groups/{group['id']}/restore", headers=_headers(staff_user)
    )
    assert restore_response.status_code == 200


async def test_attach_and_detach_modifier_group_to_product(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    product = await _create_product(authed_client, staff_user)
    group = (
        await authed_client.post(
            "/api/v1/menu/modifier-groups",
            json={"name": f"Test Group {uuid.uuid4().hex[:6]}"},
            headers=_headers(staff_user),
        )
    ).json()["data"]

    attach_response = await authed_client.post(
        f"/api/v1/menu/products/{product['id']}/modifier-groups",
        json={"modifier_group_id": group["id"]},
        headers=_headers(staff_user),
    )
    assert attach_response.status_code == 201

    list_response = await authed_client.get(
        f"/api/v1/menu/products/{product['id']}/modifier-groups", headers=_headers(staff_user)
    )
    assert len(list_response.json()["data"]) == 1

    detach_response = await authed_client.delete(
        f"/api/v1/menu/products/{product['id']}/modifier-groups/{group['id']}",
        headers=_headers(staff_user),
    )
    assert detach_response.status_code == 200


# --- Images -----------------------------------------------------------


async def test_image_upload_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    manager = await make_staff_user(role_code="kitchen_manager")
    staff = await make_staff_user(role_code="kitchen_staff")
    product = await _create_product(authed_client, manager)

    response = await authed_client.post(
        f"/api/v1/menu/products/{product['id']}/images",
        files={"file": ("test.jpg", _test_image_bytes(), "image/jpeg")},
        headers=_headers(staff),
    )
    assert response.status_code == 403


async def test_image_upload_rejects_invalid_file(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    product = await _create_product(authed_client, staff_user)

    response = await authed_client.post(
        f"/api/v1/menu/products/{product['id']}/images",
        files={"file": ("not-an-image.jpg", b"this is not a real jpeg", "image/jpeg")},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_image_upload_list_reorder_thumbnail_and_delete(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_manager")
    product = await _create_product(authed_client, staff_user)

    first_upload = await authed_client.post(
        f"/api/v1/menu/products/{product['id']}/images",
        files={"file": ("first.jpg", _test_image_bytes((10, 20, 30)), "image/jpeg")},
        headers=_headers(staff_user),
    )
    assert first_upload.status_code == 201
    first_image = first_upload.json()["data"]
    assert first_image["is_thumbnail"] is True
    assert first_image["signed_url"].startswith("http")

    second_upload = await authed_client.post(
        f"/api/v1/menu/products/{product['id']}/images",
        files={"file": ("second.jpg", _test_image_bytes((30, 20, 10)), "image/jpeg")},
        headers=_headers(staff_user),
    )
    assert second_upload.status_code == 201
    second_image = second_upload.json()["data"]
    assert second_image["is_thumbnail"] is False

    list_response = await authed_client.get(
        f"/api/v1/menu/products/{product['id']}/images", headers=_headers(staff_user)
    )
    assert len(list_response.json()["data"]) == 2

    reorder_response = await authed_client.post(
        f"/api/v1/menu/products/{product['id']}/images/reorder",
        json={"ordered_image_ids": [second_image["id"], first_image["id"]]},
        headers=_headers(staff_user),
    )
    assert reorder_response.status_code == 200

    set_thumbnail_response = await authed_client.post(
        f"/api/v1/menu/products/{product['id']}/images/{second_image['id']}/set-thumbnail",
        headers=_headers(staff_user),
    )
    assert set_thumbnail_response.status_code == 200
    assert set_thumbnail_response.json()["data"]["is_thumbnail"] is True

    product_after = await authed_client.get(
        f"/api/v1/menu/products/{product['id']}", headers=_headers(staff_user)
    )
    assert product_after.json()["data"]["image_storage_path"] is not None

    delete_response = await authed_client.delete(
        f"/api/v1/menu/products/{product['id']}/images/{first_image['id']}",
        headers=_headers(staff_user),
    )
    assert delete_response.status_code == 200

    delete_thumbnail_response = await authed_client.delete(
        f"/api/v1/menu/products/{product['id']}/images/{second_image['id']}",
        headers=_headers(staff_user),
    )
    assert delete_thumbnail_response.status_code == 200

    final_product = await authed_client.get(
        f"/api/v1/menu/products/{product['id']}", headers=_headers(staff_user)
    )
    assert final_product.json()["data"]["image_storage_path"] is None
