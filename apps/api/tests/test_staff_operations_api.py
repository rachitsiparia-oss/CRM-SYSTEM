from collections.abc import Awaitable, Callable

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


BASE = "/api/v1/staff-operations"


async def test_create_employment_profile_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="kitchen_staff")
    target = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"{BASE}/profiles",
        json={"staff_user_id": str(target.id), "joining_date": "2026-01-01"},
        headers=_headers(actor),
    )
    assert response.status_code == 403


async def test_employment_profile_rejects_reporting_cycle(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    hr = await make_staff_user(role_code="hr_manager")
    staff_a = await make_staff_user(role_code="kitchen_staff")
    staff_b = await make_staff_user(role_code="kitchen_staff")

    profile_a = await authed_client.post(
        f"{BASE}/profiles",
        json={"staff_user_id": str(staff_a.id), "joining_date": "2026-01-01"},
        headers=_headers(hr),
    )
    assert profile_a.status_code == 201, profile_a.text

    profile_b = await authed_client.post(
        f"{BASE}/profiles",
        json={
            "staff_user_id": str(staff_b.id),
            "joining_date": "2026-01-01",
            "reporting_manager_id": str(staff_a.id),
        },
        headers=_headers(hr),
    )
    assert profile_b.status_code == 201, profile_b.text

    cyclic_update = await authed_client.patch(
        f"{BASE}/profiles/{staff_a.id}",
        json={"reporting_manager_id": str(staff_b.id), "version": 1},
        headers=_headers(hr),
    )
    assert cyclic_update.status_code == 409


async def test_shift_overlap_is_rejected(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    manager = await make_staff_user(role_code="operations_manager")
    staff = await make_staff_user(role_code="kitchen_staff")

    first = await authed_client.post(
        f"{BASE}/shifts",
        json={
            "staff_user_id": str(staff.id),
            "shift_date": "2026-08-01",
            "start_at": "2026-08-01T10:00:00Z",
            "end_at": "2026-08-01T14:00:00Z",
        },
        headers=_headers(manager),
    )
    assert first.status_code == 201, first.text

    overlapping = await authed_client.post(
        f"{BASE}/shifts",
        json={
            "staff_user_id": str(staff.id),
            "shift_date": "2026-08-01",
            "start_at": "2026-08-01T12:00:00Z",
            "end_at": "2026-08-01T16:00:00Z",
        },
        headers=_headers(manager),
    )
    assert overlapping.status_code == 409


async def test_shift_publish_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    manager = await make_staff_user(role_code="operations_manager")
    staff = await make_staff_user(role_code="kitchen_staff")
    shift = await authed_client.post(
        f"{BASE}/shifts",
        json={
            "staff_user_id": str(staff.id),
            "shift_date": "2026-08-02",
            "start_at": "2026-08-02T10:00:00Z",
            "end_at": "2026-08-02T14:00:00Z",
        },
        headers=_headers(manager),
    )
    assert shift.status_code == 201

    no_publish = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"{BASE}/shifts/{shift.json()['data']['id']}/publish", headers=_headers(no_publish)
    )
    assert response.status_code == 403


async def _create_leave_type(authed_client: AsyncClient, hr: StaffUser) -> str:
    response = await authed_client.post(
        f"{BASE}/leave-types",
        json={"name": f"Type-{hr.id.hex[:8]}", "code": f"CODE{hr.id.hex[:6]}"},
        headers=_headers(hr),
    )
    assert response.status_code == 201, response.text
    result: str = response.json()["data"]["id"]
    return result


async def test_leave_overlap_is_rejected(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    hr = await make_staff_user(role_code="hr_manager")
    leave_type_id = await _create_leave_type(authed_client, hr)
    staff = await make_staff_user(role_code="kitchen_staff")

    first = await authed_client.post(
        f"{BASE}/leave-requests",
        json={"leave_type_id": leave_type_id, "start_date": "2026-08-10", "end_date": "2026-08-12"},
        headers=_headers(staff),
    )
    assert first.status_code == 201, first.text

    overlapping = await authed_client.post(
        f"{BASE}/leave-requests",
        json={"leave_type_id": leave_type_id, "start_date": "2026-08-11", "end_date": "2026-08-14"},
        headers=_headers(staff),
    )
    assert overlapping.status_code == 409


async def test_leave_approval_flow(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    hr = await make_staff_user(role_code="hr_manager")
    leave_type_id = await _create_leave_type(authed_client, hr)
    staff = await make_staff_user(role_code="kitchen_staff")

    request = await authed_client.post(
        f"{BASE}/leave-requests",
        json={"leave_type_id": leave_type_id, "start_date": "2026-09-01", "end_date": "2026-09-02"},
        headers=_headers(staff),
    )
    assert request.status_code == 201

    cannot_approve = await authed_client.post(
        f"{BASE}/leave-requests/{request.json()['data']['id']}/decide",
        json={"approve": True},
        headers=_headers(staff),
    )
    assert cannot_approve.status_code == 403

    approved = await authed_client.post(
        f"{BASE}/leave-requests/{request.json()['data']['id']}/decide",
        json={"approve": True},
        headers=_headers(hr),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "approved"


async def test_training_max_attempts_enforced(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    hr = await make_staff_user(role_code="hr_manager")
    course = await authed_client.post(
        f"{BASE}/training/courses",
        json={
            "code": f"TRN-{hr.id.hex[:8]}",
            "title": "One-shot course",
            "max_attempts": 1,
            "passing_score": 100,
        },
        headers=_headers(hr),
    )
    assert course.status_code == 201, course.text
    course_id = course.json()["data"]["id"]

    staff = await make_staff_user(role_code="kitchen_staff")
    assignment = await authed_client.post(
        f"{BASE}/training/assignments",
        json={"course_id": course_id, "staff_user_id": str(staff.id)},
        headers=_headers(hr),
    )
    assert assignment.status_code == 201, assignment.text
    assignment_id = assignment.json()["data"]["id"]

    attempt = await authed_client.post(
        f"{BASE}/training/assignments/{assignment_id}/attempts", headers=_headers(staff)
    )
    assert attempt.status_code == 201, attempt.text

    complete = await authed_client.post(
        f"{BASE}/training/attempts/{attempt.json()['data']['id']}/complete",
        json={"score": 50},
        headers=_headers(hr),
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["data"]["is_pass"] is False

    second_attempt = await authed_client.post(
        f"{BASE}/training/assignments/{assignment_id}/attempts", headers=_headers(staff)
    )
    assert second_attempt.status_code == 409


async def test_certification_verify_flow(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    hr = await make_staff_user(role_code="hr_manager")
    staff = await make_staff_user(role_code="kitchen_staff")
    certification = await authed_client.post(
        f"{BASE}/certifications",
        json={
            "staff_user_id": str(staff.id),
            "certification_type": "Food Handler",
            "issue_date": "2026-01-01",
        },
        headers=_headers(hr),
    )
    assert certification.status_code == 201, certification.text
    assert certification.json()["data"]["verification_status"] == "pending"

    verify = await authed_client.post(
        f"{BASE}/certifications/{certification.json()['data']['id']}/verify",
        json={"verification_status": "verified"},
        headers=_headers(hr),
    )
    assert verify.status_code == 200
    assert verify.json()["data"]["verification_status"] == "verified"


async def test_performance_review_finalized_is_immutable(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    hr = await make_staff_user(role_code="hr_manager")
    staff = await make_staff_user(role_code="kitchen_staff")

    review = await authed_client.post(
        f"{BASE}/reviews",
        json={
            "staff_user_id": str(staff.id),
            "cycle_label": "2026 H1",
            "period_start_date": "2026-01-01",
            "period_end_date": "2026-06-30",
        },
        headers=_headers(hr),
    )
    assert review.status_code == 201, review.text
    review_id = review.json()["data"]["id"]

    for target_status in ("in_progress", "submitted", "reviewed", "finalized"):
        transition = await authed_client.post(
            f"{BASE}/reviews/{review_id}/transition",
            json={"target_status": target_status},
            headers=_headers(hr),
        )
        assert transition.status_code == 200, transition.text

    edit_attempt = await authed_client.patch(
        f"{BASE}/reviews/{review_id}",
        json={"overall_rating": 5, "version": 1},
        headers=_headers(hr),
    )
    assert edit_attempt.status_code == 409

    ack = await authed_client.post(
        f"{BASE}/reviews/{review_id}/transition",
        json={"target_status": "acknowledged"},
        headers=_headers(staff),
    )
    assert ack.status_code == 200, ack.text


async def test_disciplinary_records_are_restricted(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    hr = await make_staff_user(role_code="hr_manager")
    staff = await make_staff_user(role_code="kitchen_staff")

    record = await authed_client.post(
        f"{BASE}/disciplinary-records",
        json={
            "staff_user_id": str(staff.id),
            "incident_date": "2026-01-01",
            "category": "Attendance",
            "description": "Late three times this month.",
            "severity": "minor",
        },
        headers=_headers(hr),
    )
    assert record.status_code == 201, record.text

    unauthorized = await authed_client.get(
        f"{BASE}/disciplinary-records",
        params={"staff_user_id": str(staff.id)},
        headers=_headers(staff),
    )
    assert unauthorized.status_code == 403

    authorized = await authed_client.get(
        f"{BASE}/disciplinary-records",
        params={"staff_user_id": str(staff.id)},
        headers=_headers(hr),
    )
    assert authorized.status_code == 200
    assert len(authorized.json()["data"]) == 1


async def test_self_service_availability_window(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff = await make_staff_user(role_code="kitchen_staff")
    other_staff = await make_staff_user(role_code="kitchen_staff")

    own_window = await authed_client.post(
        f"{BASE}/availability/{staff.id}",
        json={"availability_type": "available", "day_of_week": 1},
        headers=_headers(staff),
    )
    assert own_window.status_code == 201, own_window.text

    forbidden = await authed_client.post(
        f"{BASE}/availability/{other_staff.id}",
        json={"availability_type": "available", "day_of_week": 1},
        headers=_headers(staff),
    )
    assert forbidden.status_code == 403


async def test_staff_analytics_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.get(f"{BASE}/analytics", headers=_headers(staff_user))
    assert response.status_code == 403

    manager = await make_staff_user(role_code="hr_manager")
    response = await authed_client.get(f"{BASE}/analytics", headers=_headers(manager))
    assert response.status_code == 200
