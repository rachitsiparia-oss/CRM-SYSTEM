import random
import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


def _random_indian_phone() -> str:
    return "+91" + str(random.randint(6000000000, 9999999999))


def _create_payload(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, object] = {
        "customer_type": "individual",
        "first_name": "Anita",
        "last_name": "Verma",
        "primary_phone_e164": _random_indian_phone(),
        "primary_email": f"anita-{suffix}@example.test",
    }
    payload.update(overrides)
    return payload


async def test_list_customers_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/customers")
    assert response.status_code == 401


async def test_list_customers_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.get("/api/v1/customers", headers=_headers(staff_user))
    assert response.status_code == 403


async def test_create_customer_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="customer_support_agent")
    response = await authed_client.post(
        "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
    )
    assert response.status_code == 403


async def test_create_customer_requires_a_name(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    payload = _create_payload(first_name=None, last_name=None, display_name=None)
    response = await authed_client.post(
        "/api/v1/customers", json=payload, headers=_headers(staff_user)
    )
    assert response.status_code == 400


async def test_create_and_get_customer(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    payload = _create_payload()
    create_response = await authed_client.post(
        "/api/v1/customers", json=payload, headers=_headers(staff_user)
    )
    assert create_response.status_code == 201
    created = create_response.json()["data"]
    assert created["display_name"] == "Anita Verma"
    assert created["customer_status"] == "active"
    assert created["version"] == 1
    assert created["completed_order_count"] == 0

    get_response = await authed_client.get(
        f"/api/v1/customers/{created['id']}", headers=_headers(staff_user)
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == created["id"]


async def test_get_nonexistent_customer_is_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    response = await authed_client.get(
        f"/api/v1/customers/{uuid.uuid4()}", headers=_headers(staff_user)
    )
    assert response.status_code == 404


async def test_update_customer_conflicts_on_stale_version(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    response = await authed_client.patch(
        f"/api/v1/customers/{created['id']}",
        json={"first_name": "Renamed", "expected_version": created["version"] + 1},
        headers=_headers(staff_user),
    )
    assert response.status_code == 409


async def test_update_customer_succeeds_and_bumps_version(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    response = await authed_client.patch(
        f"/api/v1/customers/{created['id']}",
        json={"first_name": "Renamed", "expected_version": created["version"]},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["first_name"] == "Renamed"
    assert body["version"] == created["version"] + 1


async def test_archive_and_restore_customer(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    archive_response = await authed_client.request(
        "DELETE",
        f"/api/v1/customers/{created['id']}",
        json={"reason": "Customer requested account closure."},
        headers=_headers(staff_user),
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["data"]["customer_status"] == "archived"

    restore_response = await authed_client.post(
        f"/api/v1/customers/{created['id']}/restore", headers=_headers(staff_user)
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["data"]["customer_status"] == "active"


async def test_archive_customer_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    agent = await make_staff_user(role_code="customer_support_agent")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(owner)
        )
    ).json()["data"]

    response = await authed_client.request(
        "DELETE",
        f"/api/v1/customers/{created['id']}",
        json={"reason": "Should be denied."},
        headers=_headers(agent),
    )
    assert response.status_code == 403


async def test_assign_customer(authed_client: AsyncClient, make_staff_user: MakeStaffUser) -> None:
    owner = await make_staff_user(role_code="owner")
    agent = await make_staff_user(role_code="customer_support_agent")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(owner)
        )
    ).json()["data"]

    response = await authed_client.post(
        f"/api/v1/customers/{created['id']}/assign",
        json={"assigned_staff_id": str(agent.id)},
        headers=_headers(owner),
    )
    assert response.status_code == 200
    assert response.json()["data"]["assigned_staff_id"] == str(agent.id)


async def test_list_customers_filters_by_status(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    response = await authed_client.get(
        "/api/v1/customers",
        params={"customer_status": "active", "search": created["customer_number"]},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
    body = response.json()
    ids = {row["id"] for row in body["data"]}
    assert created["id"] in ids
    assert body["pagination"]["total"] >= 1


async def test_list_customers_rejects_unknown_sort_column(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    response = await authed_client.get(
        "/api/v1/customers", params={"sort": "primary_email"}, headers=_headers(staff_user)
    )
    assert response.status_code == 400


async def test_duplicate_customers_detects_phone_match(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    phone = _random_indian_phone()
    created = (
        await authed_client.post(
            "/api/v1/customers",
            json=_create_payload(primary_phone_e164=phone),
            headers=_headers(staff_user),
        )
    ).json()["data"]

    response = await authed_client.get(
        "/api/v1/customers/duplicates", params={"phone": phone}, headers=_headers(staff_user)
    )
    assert response.status_code == 200
    matches = response.json()["data"]
    assert any(m["customer"]["id"] == created["id"] for m in matches)
    assert any("exact_normalized_phone" in m["match_reasons"] for m in matches)


async def test_customer_address_second_default_replaces_first(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]
    customer_id = created["id"]

    first = await authed_client.post(
        f"/api/v1/customers/{customer_id}/addresses",
        json={
            "address_line1": "1 First St",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560001",
            "is_default": True,
        },
        headers=_headers(staff_user),
    )
    assert first.status_code == 201
    first_address = first.json()["data"]
    assert first_address["is_default"] is True

    second = await authed_client.post(
        f"/api/v1/customers/{customer_id}/addresses",
        json={
            "address_line1": "2 Second St",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560002",
            "is_default": True,
        },
        headers=_headers(staff_user),
    )
    assert second.status_code == 201

    list_response = await authed_client.get(
        f"/api/v1/customers/{customer_id}/addresses", headers=_headers(staff_user)
    )
    addresses = {row["id"]: row["is_default"] for row in list_response.json()["data"]}
    assert addresses[first_address["id"]] is False
    assert addresses[second.json()["data"]["id"]] is True


async def test_customer_notes_sensitive_note_hidden_from_role_without_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    agent = await make_staff_user(role_code="customer_support_agent")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(owner)
        )
    ).json()["data"]
    customer_id = created["id"]

    add_response = await authed_client.post(
        f"/api/v1/customers/{customer_id}/notes",
        json={
            "note_type": "complaint",
            "content": "Confidential escalation detail.",
            "is_sensitive": True,
        },
        headers=_headers(agent),
    )
    assert add_response.status_code == 201

    agent_view = await authed_client.get(
        f"/api/v1/customers/{customer_id}/notes", headers=_headers(agent)
    )
    assert agent_view.json()["data"] == []

    owner_view = await authed_client.get(
        f"/api/v1/customers/{customer_id}/notes", headers=_headers(owner)
    )
    assert len(owner_view.json()["data"]) == 1


async def test_customer_tags_add_and_remove(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]
    customer_id = created["id"]

    add_response = await authed_client.post(
        f"/api/v1/customers/{customer_id}/tags",
        json={"name": "VIP"},
        headers=_headers(staff_user),
    )
    assert add_response.status_code == 201
    tag_id = add_response.json()["data"]["id"]

    list_response = await authed_client.get(
        f"/api/v1/customers/{customer_id}/tags", headers=_headers(staff_user)
    )
    assert any(t["id"] == tag_id for t in list_response.json()["data"])

    remove_response = await authed_client.delete(
        f"/api/v1/customers/{customer_id}/tags/{tag_id}", headers=_headers(staff_user)
    )
    assert remove_response.status_code == 200

    list_after = await authed_client.get(
        f"/api/v1/customers/{customer_id}/tags", headers=_headers(staff_user)
    )
    assert list_after.json()["data"] == []


async def test_customer_consent_set_and_read(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    response = await authed_client.put(
        f"/api/v1/customers/{created['id']}/consents/whatsapp_marketing",
        json={"status": "granted", "source": "signup_form"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "granted"
    assert body["granted_at"] is not None


async def test_merge_preview_and_execute(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    source = (
        await authed_client.post(
            "/api/v1/customers",
            json=_create_payload(first_name="Dupe", last_name="One"),
            headers=_headers(staff_user),
        )
    ).json()["data"]
    surviving = (
        await authed_client.post(
            "/api/v1/customers",
            json=_create_payload(first_name="Dupe", last_name="Two"),
            headers=_headers(staff_user),
        )
    ).json()["data"]

    await authed_client.post(
        f"/api/v1/customers/{source['id']}/tags",
        json={"name": "Loyal"},
        headers=_headers(staff_user),
    )

    preview = await authed_client.post(
        "/api/v1/customers/merge/preview",
        params={
            "source_customer_id": source["id"],
            "surviving_customer_id": surviving["id"],
        },
        headers=_headers(staff_user),
    )
    assert preview.status_code == 200
    preview_body = preview.json()["data"]
    assert preview_body["source_tag_count"] == 1
    assert "last_name" in preview_body["conflicting_fields"]

    merge = await authed_client.post(
        "/api/v1/customers/merge",
        json={
            "source_customer_id": source["id"],
            "surviving_customer_id": surviving["id"],
            "reason": "Confirmed duplicate customer records.",
            "field_resolutions": [],
        },
        headers=_headers(staff_user),
    )
    assert merge.status_code == 200
    assert merge.json()["data"]["id"] == surviving["id"]

    source_after = await authed_client.get(
        f"/api/v1/customers/{source['id']}", headers=_headers(staff_user)
    )
    assert source_after.json()["data"]["customer_status"] == "merged"
    assert source_after.json()["data"]["merged_into_customer_id"] == surviving["id"]

    tags_after = await authed_client.get(
        f"/api/v1/customers/{surviving['id']}/tags", headers=_headers(staff_user)
    )
    assert any(t["name"] == "Loyal" for t in tags_after.json()["data"])


async def test_merge_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    agent = await make_staff_user(role_code="customer_support_agent")
    source = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(owner)
        )
    ).json()["data"]
    surviving = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(owner)
        )
    ).json()["data"]

    response = await authed_client.post(
        "/api/v1/customers/merge",
        json={
            "source_customer_id": source["id"],
            "surviving_customer_id": surviving["id"],
            "reason": "Should be denied.",
            "field_resolutions": [],
        },
        headers=_headers(agent),
    )
    assert response.status_code == 403


async def test_merge_rejects_self_merge(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    created = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    response = await authed_client.post(
        "/api/v1/customers/merge",
        json={
            "source_customer_id": created["id"],
            "surviving_customer_id": created["id"],
            "reason": "Should be rejected.",
            "field_resolutions": [],
        },
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_double_merge_of_source_is_rejected(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    source = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]
    surviving_a = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]
    surviving_b = (
        await authed_client.post(
            "/api/v1/customers", json=_create_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    first_merge = await authed_client.post(
        "/api/v1/customers/merge",
        json={
            "source_customer_id": source["id"],
            "surviving_customer_id": surviving_a["id"],
            "reason": "First merge.",
            "field_resolutions": [],
        },
        headers=_headers(staff_user),
    )
    assert first_merge.status_code == 200

    second_merge = await authed_client.post(
        "/api/v1/customers/merge",
        json={
            "source_customer_id": source["id"],
            "surviving_customer_id": surviving_b["id"],
            "reason": "Should be rejected — already merged.",
            "field_resolutions": [],
        },
        headers=_headers(staff_user),
    )
    assert second_merge.status_code == 409
