"""HTTP-layer authentication/authorization tests for the feedback,
complaints, and service-recovery routers, plus integration-hook coverage
(order->review-request scheduling, complaint->conversation linking).
Service-layer workflow correctness is covered by test_feedback_service.py/
test_complaints_service.py/test_service_recovery_service.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.complaints import service as complaints_service
from app.complaints.schemas import ComplaintCreateIn
from app.db.models import (
    ConversationLink,
    Customer,
    Order,
    Permission,
    Role,
    RolePermission,
    StaffRole,
    StaffUser,
)
from app.feedback import integrations as feedback_integrations
from app.feedback.errors import DuplicateReviewRequestError
from httpx import AsyncClient
from sqlalchemy import select
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
        "display_name": "Test Customer",
        "first_name": "Test",
        "last_name": "Customer",
        "primary_phone_e164": "+919876543210",
    }
    fields.update(overrides)
    customer = Customer(**fields)
    session.add(customer)
    await session.flush()
    return customer


async def _make_order(session: AsyncSession, **overrides: object) -> Order:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "order_number": f"ORD-{suffix}",
        "source": "manual",
        "order_type": "takeaway",
        "status": "completed",
        "payment_status": "paid",
    }
    fields.update(overrides)
    order = Order(**fields)
    session.add(order)
    await session.flush()
    return order


async def _make_role_with_permissions(db_session: AsyncSession, *, codes: list[str]) -> Role:
    role = Role(id=uuid.uuid4(), code=f"test-role-{uuid.uuid4().hex[:10]}", name="Test Role")
    db_session.add(role)
    await db_session.flush()
    permission_ids = await db_session.scalars(
        select(Permission.id).where(Permission.code.in_(codes))
    )
    ids = list(permission_ids)
    assert len(ids) == len(codes), f"Expected all of {codes!r} to already be seeded permissions."
    for permission_id in ids:
        db_session.add(
            RolePermission(role_id=role.id, permission_id=permission_id, scope_type="all")
        )
    await db_session.flush()
    return role


async def _complaint_payload(customer_id: uuid.UUID, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "customer_id": str(customer_id),
        "source_type": "direct",
        "category": "delay",
        "title": "Order delivered late",
        "description": "Order arrived an hour late.",
        "severity": "medium",
        "priority": "normal",
    }
    payload.update(overrides)
    return payload


# --- Feedback router ---------------------------------------------------------


async def test_list_feedback_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/feedback")
    assert response.status_code == 401


async def test_list_feedback_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/feedback", headers=_headers(outsider))
    assert response.status_code == 403


async def test_create_feedback_succeeds_for_permitted_role(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="customer_support_agent")
    customer = await _make_customer(db_session)
    response = await authed_client.post(
        "/api/v1/feedback",
        json={
            "customer_id": str(customer.id),
            "source": "manual_entry",
            "comment": "Great experience overall.",
        },
        headers=_headers(actor),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["status"] == "new"


# --- Complaints router ---------------------------------------------------


async def test_create_complaint_requires_permission(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    customer = await _make_customer(db_session)
    response = await authed_client.post(
        "/api/v1/complaints",
        json=await _complaint_payload(customer.id),
        headers=_headers(outsider),
    )
    assert response.status_code == 403


async def test_get_complaint_denied_when_not_assigned_and_not_view_all(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    creator = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await complaints_service.create_complaint(
        db_session,
        actor=creator,
        payload=ComplaintCreateIn.model_validate(await _complaint_payload(customer.id)),
    )

    # A role with `complaints.view` but neither `.view_all` nor an
    # assignment to this complaint must be denied.
    limited_role = await _make_role_with_permissions(db_session, codes=["complaints.view"])
    limited_actor = await make_staff_user(role_code=None)
    db_session.add(StaffRole(staff_user_id=limited_actor.id, role_id=limited_role.id))
    await db_session.flush()

    response = await authed_client.get(
        f"/api/v1/complaints/{complaint.id}", headers=_headers(limited_actor)
    )
    assert response.status_code == 403


async def test_get_complaint_allowed_when_assigned(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    creator = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await complaints_service.create_complaint(
        db_session,
        actor=creator,
        payload=ComplaintCreateIn.model_validate(await _complaint_payload(customer.id)),
    )

    limited_role = await _make_role_with_permissions(db_session, codes=["complaints.view"])
    limited_actor = await make_staff_user(role_code=None)
    db_session.add(StaffRole(staff_user_id=limited_actor.id, role_id=limited_role.id))
    await db_session.flush()
    complaint.assigned_staff_id = limited_actor.id
    await db_session.flush()

    response = await authed_client.get(
        f"/api/v1/complaints/{complaint.id}", headers=_headers(limited_actor)
    )
    assert response.status_code == 200


async def test_hr_sensitive_complaint_requires_additional_permission(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    creator = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await complaints_service.create_complaint(
        db_session,
        actor=creator,
        payload=ComplaintCreateIn.model_validate(
            await _complaint_payload(customer.id, category="staff_behavior")
        ),
    )
    assert complaint.is_hr_sensitive is True

    role = await _make_role_with_permissions(
        db_session, codes=["complaints.view_all", "complaints.view"]
    )
    actor = await make_staff_user(role_code=None)
    db_session.add(StaffRole(staff_user_id=actor.id, role_id=role.id))
    await db_session.flush()

    response = await authed_client.get(
        f"/api/v1/complaints/{complaint.id}", headers=_headers(actor)
    )
    assert response.status_code == 403


async def test_complaint_transition_gated_target_enforced_at_router(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    creator = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await complaints_service.create_complaint(
        db_session,
        actor=creator,
        payload=ComplaintCreateIn.model_validate(await _complaint_payload(customer.id)),
    )
    complaint.assigned_staff_id = None

    role = await _make_role_with_permissions(
        db_session,
        codes=["complaints.view_all", "complaints.view", "complaints.transition"],
    )
    actor = await make_staff_user(role_code=None)
    db_session.add(StaffRole(staff_user_id=actor.id, role_id=role.id))
    await db_session.flush()

    ack_response = await authed_client.post(
        f"/api/v1/complaints/{complaint.id}/transition",
        json={"target_status": "acknowledged"},
        headers=_headers(actor),
    )
    assert ack_response.status_code == 200, ack_response.text

    invest_response = await authed_client.post(
        f"/api/v1/complaints/{complaint.id}/transition",
        json={"target_status": "investigating"},
        headers=_headers(actor),
    )
    assert invest_response.status_code == 200, invest_response.text

    proposed_response = await authed_client.post(
        f"/api/v1/complaints/{complaint.id}/transition",
        json={"target_status": "resolution_proposed"},
        headers=_headers(actor),
    )
    assert proposed_response.status_code == 200, proposed_response.text

    resolve_response = await authed_client.post(
        f"/api/v1/complaints/{complaint.id}/transition",
        json={"target_status": "resolved"},
        headers=_headers(actor),
    )
    assert resolve_response.status_code == 403


# --- Service recovery router -----------------------------------------------


async def test_propose_recovery_action_requires_permission(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    creator = await make_staff_user(role_code="owner")
    outsider = await make_staff_user(role_code=None)
    customer = await _make_customer(db_session)
    complaint = await complaints_service.create_complaint(
        db_session,
        actor=creator,
        payload=ComplaintCreateIn.model_validate(await _complaint_payload(customer.id)),
    )
    response = await authed_client.post(
        f"/api/v1/complaints/{complaint.id}/recovery-actions",
        json={"recovery_type": "apology_only", "description": "Apology."},
        headers=_headers(outsider),
    )
    assert response.status_code == 403


async def test_propose_and_approve_recovery_action_via_api(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await complaints_service.create_complaint(
        db_session,
        actor=actor,
        payload=ComplaintCreateIn.model_validate(await _complaint_payload(customer.id)),
    )
    propose_response = await authed_client.post(
        f"/api/v1/complaints/{complaint.id}/recovery-actions",
        json={"recovery_type": "loyalty_credit", "points": 100, "description": "100 points."},
        headers=_headers(actor),
    )
    assert propose_response.status_code == 201, propose_response.text
    action_id = propose_response.json()["data"]["id"]

    execute_response = await authed_client.post(
        f"/api/v1/service-recovery/actions/{action_id}/execute", headers=_headers(actor)
    )
    assert execute_response.status_code == 200, execute_response.text
    assert execute_response.json()["data"]["status"] == "completed"


async def test_execute_recovery_action_requires_permission(
    authed_client: AsyncClient, db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    outsider = await make_staff_user(role_code=None)
    customer = await _make_customer(db_session)
    complaint = await complaints_service.create_complaint(
        db_session,
        actor=actor,
        payload=ComplaintCreateIn.model_validate(await _complaint_payload(customer.id)),
    )
    propose_response = await authed_client.post(
        f"/api/v1/complaints/{complaint.id}/recovery-actions",
        json={"recovery_type": "apology_only", "description": "Apology."},
        headers=_headers(actor),
    )
    action_id = propose_response.json()["data"]["id"]

    response = await authed_client.post(
        f"/api/v1/service-recovery/actions/{action_id}/execute", headers=_headers(outsider)
    )
    assert response.status_code == 403


# --- Integrations ------------------------------------------------------------


async def test_create_complaint_links_a_conversation(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await complaints_service.create_complaint(
        db_session,
        actor=actor,
        payload=ComplaintCreateIn.model_validate(await _complaint_payload(customer.id)),
    )
    assert complaint.conversation_id is not None
    link = await db_session.scalar(
        select(ConversationLink).where(
            ConversationLink.linked_type == "complaint", ConversationLink.linked_id == complaint.id
        )
    )
    assert link is not None
    assert link.conversation_id == complaint.conversation_id


async def test_schedule_order_review_request_only_on_completed_order_with_customer(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)

    from app.db.models import ReviewRequest

    await feedback_integrations.schedule_order_review_request(
        db_session, actor=actor, order=order, new_status="preparing"
    )
    none_created = await db_session.scalar(
        select(ReviewRequest).where(ReviewRequest.order_id == order.id)
    )
    assert none_created is None

    await feedback_integrations.schedule_order_review_request(
        db_session, actor=actor, order=order, new_status="completed"
    )
    created = await db_session.scalar(
        select(ReviewRequest).where(ReviewRequest.order_id == order.id)
    )
    assert created is not None


async def test_schedule_order_review_request_swallows_duplicate(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)

    await feedback_integrations.schedule_order_review_request(
        db_session, actor=actor, order=order, new_status="completed"
    )
    # Calling again (as a retried transition would) must not raise even
    # though the underlying idempotency_key already exists.
    try:
        await feedback_integrations.schedule_order_review_request(
            db_session, actor=actor, order=order, new_status="completed"
        )
    except DuplicateReviewRequestError:
        pytest.fail("schedule_order_review_request must swallow DuplicateReviewRequestError")
