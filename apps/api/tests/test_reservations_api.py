import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]

# A Monday, matching the seeded Monday-Thursday 11:00-23:00 business hours
# (PROJECT_PLAN.md section 3.3) — independent of "today" so these tests
# stay valid regardless of when they run.
_A_MONDAY = "2026-08-10"


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _create_dining_area(authed_client: AsyncClient, staff_user: StaffUser) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    response = await authed_client.post(
        "/api/v1/reservations/dining-areas",
        json={"code": f"area-{suffix}", "name": "Test Area"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()["data"]
    return result


async def _create_table(
    authed_client: AsyncClient, staff_user: StaffUser, dining_area_id: str, **overrides: Any
) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "dining_area_id": dining_area_id,
        "table_number": f"T-{suffix}",
        "capacity": 4,
    }
    payload.update(overrides)
    response = await authed_client.post(
        "/api/v1/reservations/tables", json=payload, headers=_headers(staff_user)
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()["data"]
    return result


def _reservation_payload(dining_area_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "guest_name": "Test Guest",
        "party_size": 2,
        "reservation_date": _A_MONDAY,
        "start_time": "19:00:00",
        "dining_area_id": dining_area_id,
        "source": "phone",
        "idempotency_key": f"test-{uuid.uuid4().hex}",
    }
    payload.update(overrides)
    return payload


async def _create_reservation(
    authed_client: AsyncClient, staff_user: StaffUser, dining_area_id: str, **overrides: Any
) -> dict[str, Any]:
    response = await authed_client.post(
        "/api/v1/reservations",
        json=_reservation_payload(dining_area_id, **overrides),
        headers=_headers(staff_user),
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()["data"]
    return result


# --- Create ------------------------------------------------------------------


async def test_create_reservation_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    response = await authed_client.post(
        "/api/v1/reservations",
        json=_reservation_payload(str(uuid.uuid4())),
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


async def test_create_reservation_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    reservation = await _create_reservation(authed_client, staff_user, dining_area["id"])
    assert reservation["status"] == "requested"
    assert reservation["is_walk_in"] is False


async def test_create_reservation_is_idempotent(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    key = f"idem-{uuid.uuid4().hex}"
    payload = _reservation_payload(dining_area["id"], idempotency_key=key)
    first = await authed_client.post(
        "/api/v1/reservations", json=payload, headers=_headers(staff_user)
    )
    second = await authed_client.post(
        "/api/v1/reservations", json=payload, headers=_headers(staff_user)
    )
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


async def test_create_reservation_rejects_large_party(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    response = await authed_client.post(
        "/api/v1/reservations",
        json=_reservation_payload(dining_area["id"], party_size=25),
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


# --- Transition and approval ---------------------------------------------


async def test_transition_rejects_skipping_steps(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    reservation = await _create_reservation(authed_client, staff_user, dining_area["id"])

    response = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/transition",
        json={"new_status": "confirmed"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


async def test_approval_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    await _create_table(authed_client, staff_user, dining_area["id"], capacity=4)
    reservation = await _create_reservation(authed_client, staff_user, dining_area["id"])

    await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/transition",
        json={"new_status": "pending_review"},
        headers=_headers(staff_user),
    )
    response = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/approval",
        json={"approve": True},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "approved"


async def test_approval_fails_with_no_table_available(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    # Deliberately no table created in this dining area.
    reservation = await _create_reservation(authed_client, staff_user, dining_area["id"])
    await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/transition",
        json={"new_status": "pending_review"},
        headers=_headers(staff_user),
    )
    response = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/approval",
        json={"approve": True},
        headers=_headers(staff_user),
    )
    assert response.status_code == 409


async def test_rejection_requires_a_reason(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    reservation = await _create_reservation(authed_client, staff_user, dining_area["id"])
    await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/transition",
        json={"new_status": "pending_review"},
        headers=_headers(staff_user),
    )
    response = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/approval",
        json={"approve": False},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400

    response = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/approval",
        json={"approve": False, "reason": "Fully booked."},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "rejected"


async def test_approval_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, owner)
    reservation = await _create_reservation(authed_client, owner, dining_area["id"])
    await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/transition",
        json={"new_status": "pending_review"},
        headers=_headers(owner),
    )

    # front_of_house_staff has reservations.transition/create but not
    # reservations.approve.
    limited = await make_staff_user(role_code="front_of_house_staff")
    response = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/approval",
        json={"approve": True},
        headers=_headers(limited),
    )
    assert response.status_code == 403


async def test_cancel_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, owner)
    reservation = await _create_reservation(authed_client, owner, dining_area["id"])

    limited = await make_staff_user(role_code="front_of_house_staff")
    response = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/transition",
        json={"new_status": "cancelled_by_customer"},
        headers=_headers(limited),
    )
    assert response.status_code == 403


# --- Walk-in ------------------------------------------------------------


async def test_walk_in_lands_at_arrived(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    response = await authed_client.post(
        "/api/v1/reservations/walk-in",
        json={
            "guest_name": "Walk-in Test Guest",
            "phone_e164": "9812345670",
            "party_size": 2,
            "dining_area_id": dining_area["id"],
        },
        headers=_headers(staff_user),
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "arrived"
    assert data["is_walk_in"] is True
    assert data["approved_by"] is not None


# --- Table assignment -----------------------------------------------------


async def test_assign_and_unassign_tables(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    table = await _create_table(authed_client, staff_user, dining_area["id"], capacity=4)
    reservation = await _create_reservation(authed_client, staff_user, dining_area["id"])
    await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/transition",
        json={"new_status": "pending_review"},
        headers=_headers(staff_user),
    )
    await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/approval",
        json={"approve": True},
        headers=_headers(staff_user),
    )

    response = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/assign-tables",
        json={"table_ids": [table["id"]]},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200, response.text
    assignments = response.json()["data"]
    assert len(assignments) == 1
    assert assignments[0]["restaurant_table_id"] == table["id"]

    unassign = await authed_client.post(
        f"/api/v1/reservations/{reservation['id']}/unassign-tables",
        headers=_headers(staff_user),
    )
    assert unassign.status_code == 200


# --- Tables / dining areas --------------------------------------------------


async def test_create_dining_area_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="front_of_house_staff")
    response = await authed_client.post(
        "/api/v1/reservations/dining-areas",
        json={"code": f"area-{uuid.uuid4().hex[:8]}", "name": "Blocked Area"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


async def test_merge_and_split_tables(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    primary = await _create_table(authed_client, staff_user, dining_area["id"], capacity=6)
    secondary = await _create_table(authed_client, staff_user, dining_area["id"], capacity=6)

    merge_response = await authed_client.post(
        f"/api/v1/reservations/tables/{primary['id']}/merge",
        json={"secondary_table_ids": [secondary["id"]]},
        headers=_headers(staff_user),
    )
    assert merge_response.status_code == 200, merge_response.text
    assert merge_response.json()["data"][0]["status"] == "merged"

    split_response = await authed_client.post(
        f"/api/v1/reservations/tables/{primary['id']}/split",
        json={},
        headers=_headers(staff_user),
    )
    assert split_response.status_code == 200
    assert split_response.json()["data"][0]["status"] == "available"


async def test_table_status_transition_rejects_invalid_target(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    table = await _create_table(authed_client, staff_user, dining_area["id"])

    response = await authed_client.post(
        f"/api/v1/reservations/tables/{table['id']}/status",
        json={"new_status": "merged"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 400


# --- Availability ----------------------------------------------------------


async def test_availability_endpoint_returns_created_table(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)
    table = await _create_table(authed_client, staff_user, dining_area["id"], capacity=4)

    response = await authed_client.get(
        "/api/v1/reservations/availability",
        params={
            "target_date": _A_MONDAY,
            "start_time": "19:00:00",
            "party_size": 2,
            "dining_area_id": dining_area["id"],
        },
        headers=_headers(staff_user),
    )
    assert response.status_code == 200, response.text
    ids = [t["id"] for t in response.json()["data"]]
    assert table["id"] in ids


# --- Waitlist ----------------------------------------------------------


async def test_waitlist_create_notify_and_cancel(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)

    create_response = await authed_client.post(
        "/api/v1/reservations/waitlist",
        json={
            "guest_name": "Waitlist Test Guest",
            "party_size": 3,
            "dining_area_id": dining_area["id"],
        },
        headers=_headers(staff_user),
    )
    assert create_response.status_code == 201, create_response.text
    entry = create_response.json()["data"]
    assert entry["status"] == "waiting"

    notify_response = await authed_client.post(
        f"/api/v1/reservations/waitlist/{entry['id']}/notify", headers=_headers(staff_user)
    )
    assert notify_response.status_code == 200
    assert notify_response.json()["data"]["status"] == "notified"

    cancel_response = await authed_client.post(
        f"/api/v1/reservations/waitlist/{entry['id']}/cancel",
        json={"reason": "Guest left."},
        headers=_headers(staff_user),
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "cancelled"


async def test_waitlist_promote_links_reservation(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    dining_area = await _create_dining_area(authed_client, staff_user)

    entry_response = await authed_client.post(
        "/api/v1/reservations/waitlist",
        json={
            "guest_name": "Promotable Guest",
            "party_size": 2,
            "dining_area_id": dining_area["id"],
        },
        headers=_headers(staff_user),
    )
    entry = entry_response.json()["data"]

    walk_in_response = await authed_client.post(
        "/api/v1/reservations/walk-in",
        json={
            "guest_name": "Promotable Guest",
            "party_size": 2,
            "dining_area_id": dining_area["id"],
        },
        headers=_headers(staff_user),
    )
    reservation = walk_in_response.json()["data"]

    promote_response = await authed_client.post(
        f"/api/v1/reservations/waitlist/{entry['id']}/promote",
        json={"reservation_id": reservation["id"]},
        headers=_headers(staff_user),
    )
    assert promote_response.status_code == 200, promote_response.text
    assert promote_response.json()["data"]["status"] == "promoted"
    assert promote_response.json()["data"]["promoted_reservation_id"] == reservation["id"]


async def test_waitlist_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="hr_manager")
    response = await authed_client.post(
        "/api/v1/reservations/waitlist",
        json={"guest_name": "Blocked Guest", "party_size": 2},
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


# --- Customer stats and dashboard ------------------------------------------


async def test_customer_stats_endpoint(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    response = await authed_client.get(
        f"/api/v1/reservations/customers/{uuid.uuid4()}/stats", headers=_headers(staff_user)
    )
    assert response.status_code == 200
    assert response.json()["data"]["lifetime_visit_count"] == 0


async def test_dashboard_stats_endpoint(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="owner")
    response = await authed_client.get(
        "/api/v1/reservations/dashboard/stats",
        params={"target_date": _A_MONDAY},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200
