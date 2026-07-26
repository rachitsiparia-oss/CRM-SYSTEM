import random
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

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


def _lead_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "lead_type": "general_sales_enquiry",
        "display_name": "Prospective Diner",
        "source": "website",
        "phone_e164": _random_indian_phone(),
    }
    payload.update(overrides)
    return payload


async def test_list_leads_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/leads")
    assert response.status_code == 401


async def test_create_lead_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
    )
    assert response.status_code == 403


async def test_create_and_get_lead(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    create_response = await authed_client.post(
        "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
    )
    assert create_response.status_code == 201
    created = create_response.json()["data"]
    assert created["status"] == "new"
    assert created["priority"] == "normal"
    assert created["do_not_contact"] is False

    get_response = await authed_client.get(
        f"/api/v1/leads/{created['id']}", headers=_headers(staff_user)
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == created["id"]


async def test_get_nonexistent_lead_is_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    response = await authed_client.get(
        f"/api/v1/leads/{uuid.uuid4()}", headers=_headers(staff_user)
    )
    assert response.status_code == 404


async def test_update_lead_conflicts_on_stale_version(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    response = await authed_client.patch(
        f"/api/v1/leads/{created['id']}",
        json={"description": "Updated.", "expected_version": created["version"] + 1},
        headers=_headers(staff_user),
    )
    assert response.status_code == 409


async def test_transition_lead_valid_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/transition",
        json={"new_status": "contacted"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "contacted"


async def test_transition_lead_rejects_invalid_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/transition",
        json={"new_status": "negotiating"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_transition_lead_to_lost_requires_reason(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    missing_reason = await authed_client.post(
        f"/api/v1/leads/{created['id']}/transition",
        json={"new_status": "lost"},
        headers=_headers(staff_user),
    )
    assert missing_reason.status_code == 400

    with_reason = await authed_client.post(
        f"/api/v1/leads/{created['id']}/transition",
        json={"new_status": "lost", "lost_reason": "budget"},
        headers=_headers(staff_user),
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["data"]["status"] == "lost"
    assert with_reason.json()["data"]["lost_reason"] == "budget"


async def test_transition_lead_can_never_reach_won_directly(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    """`won` must only be reachable through the conversion endpoint —
    app.leads.states.is_transition_allowed always returns False for it,
    even from a status that would otherwise be a legal transition target."""
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]
    await authed_client.post(
        f"/api/v1/leads/{created['id']}/transition",
        json={"new_status": "contacted"},
        headers=_headers(staff_user),
    )

    response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/transition",
        json={"new_status": "won"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_do_not_contact_blocks_new_follow_ups(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    dnc_response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/do-not-contact",
        params={"value": True},
        headers=_headers(staff_user),
    )
    assert dnc_response.status_code == 200
    assert dnc_response.json()["data"]["do_not_contact"] is True

    follow_up_response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/follow-ups",
        json={
            "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "assigned_to": str(staff_user.id),
        },
        headers=_headers(staff_user),
    )
    assert follow_up_response.status_code == 400


async def test_schedule_complete_and_reschedule_follow_up(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    create_response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/follow-ups",
        json={
            "scheduled_at": scheduled_at,
            "assigned_to": str(staff_user.id),
            "purpose": "Confirm menu.",
        },
        headers=_headers(staff_user),
    )
    assert create_response.status_code == 201
    follow_up = create_response.json()["data"]
    assert follow_up["status"] == "scheduled"

    complete_response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/follow-ups/{follow_up['id']}/complete",
        json={"outcome": "Customer confirmed interest."},
        headers=_headers(staff_user),
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["data"]["status"] == "completed"

    reschedule_at = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    reschedule_response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/follow-ups/{follow_up['id']}/reschedule",
        json={"scheduled_at": reschedule_at, "reason": "Customer asked to push it out."},
        headers=_headers(staff_user),
    )
    assert reschedule_response.status_code == 200
    assert reschedule_response.json()["data"]["status"] == "scheduled"


async def test_duplicate_leads_detects_phone_match(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    phone = _random_indian_phone()
    created = (
        await authed_client.post(
            "/api/v1/leads",
            json=_lead_payload(phone_e164=phone),
            headers=_headers(staff_user),
        )
    ).json()["data"]

    response = await authed_client.get(
        "/api/v1/leads/duplicates", params={"phone": phone}, headers=_headers(staff_user)
    )
    assert response.status_code == 200
    matches = response.json()["data"]
    assert any(m["lead"]["id"] == created["id"] for m in matches)


async def test_conversion_preview_and_execute_creates_new_customer(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    preview = await authed_client.get(
        f"/api/v1/leads/{created['id']}/convert/preview", headers=_headers(staff_user)
    )
    assert preview.status_code == 200
    assert preview.json()["data"]["will_create_new_customer"] is True

    idempotency_key = f"convert-{uuid.uuid4()}"
    convert_response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/convert",
        json={"idempotency_key": idempotency_key},
        headers=_headers(staff_user),
    )
    assert convert_response.status_code == 200
    customer = convert_response.json()["data"]
    assert customer["primary_phone_e164"] == created["phone_e164"]

    lead_after = await authed_client.get(
        f"/api/v1/leads/{created['id']}", headers=_headers(staff_user)
    )
    lead_body = lead_after.json()["data"]
    assert lead_body["status"] == "won"
    assert lead_body["won_customer_id"] == customer["id"]


async def test_conversion_is_idempotent_on_repeat_call(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    idempotency_key = f"convert-{uuid.uuid4()}"
    first = await authed_client.post(
        f"/api/v1/leads/{created['id']}/convert",
        json={"idempotency_key": idempotency_key},
        headers=_headers(staff_user),
    )
    second = await authed_client.post(
        f"/api/v1/leads/{created['id']}/convert",
        json={"idempotency_key": idempotency_key},
        headers=_headers(staff_user),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


async def test_conversion_reuses_matched_existing_customer(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    phone = _random_indian_phone()
    existing_customer = (
        await authed_client.post(
            "/api/v1/customers",
            json={
                "customer_type": "individual",
                "first_name": "Existing",
                "last_name": "Customer",
                "primary_phone_e164": phone,
            },
            headers=_headers(staff_user),
        )
    ).json()["data"]

    lead = (
        await authed_client.post(
            "/api/v1/leads",
            json=_lead_payload(phone_e164=phone),
            headers=_headers(staff_user),
        )
    ).json()["data"]

    preview = await authed_client.get(
        f"/api/v1/leads/{lead['id']}/convert/preview", headers=_headers(staff_user)
    )
    assert preview.json()["data"]["will_create_new_customer"] is False
    assert any(
        c["id"] == existing_customer["id"]
        for c in preview.json()["data"]["possible_customer_matches"]
    )

    convert_response = await authed_client.post(
        f"/api/v1/leads/{lead['id']}/convert",
        json={
            "existing_customer_id": existing_customer["id"],
            "idempotency_key": f"convert-{uuid.uuid4()}",
        },
        headers=_headers(staff_user),
    )
    assert convert_response.status_code == 200
    assert convert_response.json()["data"]["id"] == existing_customer["id"]


async def test_conversion_rejects_lost_lead(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]
    await authed_client.post(
        f"/api/v1/leads/{created['id']}/transition",
        json={"new_status": "lost", "lost_reason": "budget"},
        headers=_headers(staff_user),
    )

    response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/convert",
        json={"idempotency_key": f"convert-{uuid.uuid4()}"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_convert_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    manager = await make_staff_user(role_code="operations_manager")
    kitchen = await make_staff_user(role_code="kitchen_staff")
    created = (
        await authed_client.post("/api/v1/leads", json=_lead_payload(), headers=_headers(manager))
    ).json()["data"]

    response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/convert",
        json={"idempotency_key": f"convert-{uuid.uuid4()}"},
        headers=_headers(kitchen),
    )
    assert response.status_code == 403


async def test_archive_lead_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    manager = await make_staff_user(role_code="operations_manager")
    agent = await make_staff_user(role_code="customer_support_agent")
    created = (
        await authed_client.post("/api/v1/leads", json=_lead_payload(), headers=_headers(manager))
    ).json()["data"]

    response = await authed_client.request(
        "DELETE",
        f"/api/v1/leads/{created['id']}",
        json={"reason": "Should be denied."},
        headers=_headers(agent),
    )
    assert response.status_code == 403


async def test_archive_and_restore_lead(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]

    archive_response = await authed_client.request(
        "DELETE",
        f"/api/v1/leads/{created['id']}",
        json={"reason": "Duplicate enquiry."},
        headers=_headers(staff_user),
    )
    assert archive_response.status_code == 200

    get_after_archive = await authed_client.get(
        f"/api/v1/leads/{created['id']}", headers=_headers(staff_user)
    )
    assert get_after_archive.status_code == 404

    restore_response = await authed_client.post(
        f"/api/v1/leads/{created['id']}/restore", headers=_headers(staff_user)
    )
    assert restore_response.status_code == 200

    get_after_restore = await authed_client.get(
        f"/api/v1/leads/{created['id']}", headers=_headers(staff_user)
    )
    assert get_after_restore.status_code == 200


async def test_list_leads_filters_overdue_follow_up(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    created = (
        await authed_client.post(
            "/api/v1/leads", json=_lead_payload(), headers=_headers(staff_user)
        )
    ).json()["data"]
    await authed_client.post(
        f"/api/v1/leads/{created['id']}/follow-ups",
        json={
            "scheduled_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
            "assigned_to": str(staff_user.id),
        },
        headers=_headers(staff_user),
    )

    response = await authed_client.get(
        "/api/v1/leads",
        params={"overdue_follow_up": True, "search": created["lead_number"]},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["data"]}
    assert created["id"] in ids
