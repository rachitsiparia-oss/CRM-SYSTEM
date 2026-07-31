"""HTTP-layer permission tests for the offers router.

`customer_support_agent` holds `offers.view` + `offers.redeem` (service
recovery at the counter) but not `offers.manage`/`offers.approve`/
`offers.reverse`. `marketing_manager` owns offer configuration
(`offers.manage`/`offers.approve`) but not `offers.redeem`/`offers.reverse`.
`finance_manager` holds `offers.reverse` only. See
app/permissions/role_matrix.py's own comments for that split.

The offer-transition endpoint has a documented special case
(app/offers/router.py's `transition_offer`): moving an offer into
`approved` requires `offers.approve` specifically, not just
`offers.manage` — a role with `offers.manage` alone must still be
rejected. No seeded role carries that exact split, so this file builds one
directly from existing `Permission` rows (already synced into the test
database by `app.permissions.seed`) to exercise it precisely.

Business-rule correctness (benefit math, redemption lifecycle, coupon
gating) is covered by test_offers_benefit.py and test_offers_redemptions.py;
this file checks only the router's own responsibility: permission
enforcement.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from app.commercial_rules.schema import RuleCondition
from app.db.models import Customer, Order, Permission, Role, RolePermission, StaffRole, StaffUser
from app.offers import service as offers_service
from app.offers.benefit import PercentageBenefit
from app.offers.schemas import OfferCreateIn, OfferVersionCreateIn
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]

_ALWAYS_TRUE_RULE = RuleCondition(fact="customer.completed_order_count", operator="gte", value=0)


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


def _offer_payload(**overrides: Any) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "offer_code": f"OFFER-{suffix}",
        "internal_name": f"Offer {suffix}",
        "customer_facing_name": f"Offer {suffix}",
        "offer_type": "percentage_discount",
        "requires_code": False,
        "initial_version": {
            "eligibility_rule": {
                "kind": "condition",
                "fact": "customer.completed_order_count",
                "operator": "gte",
                "value": 0,
            },
            "benefit_rule": {"kind": "percentage", "percent": "10"},
            "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
    }
    payload.update(overrides)
    return payload


async def _create_offer_via_api(authed_client: AsyncClient, marketer: StaffUser) -> str:
    response = await authed_client.post(
        "/api/v1/offers", json=_offer_payload(), headers=_headers(marketer)
    )
    assert response.status_code == 201, response.text
    offer_id: str = response.json()["data"]["id"]
    return offer_id


async def _make_role_with_permissions(db_session: AsyncSession, *, codes: list[str]) -> Role:
    role = Role(
        id=uuid.uuid4(),
        code=f"test-role-{uuid.uuid4().hex[:10]}",
        name="Test Role",
        is_system_role=False,
        is_active=True,
    )
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


async def _make_customer(session: AsyncSession, **overrides: object) -> Customer:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": "Test Customer",
        "first_name": "Test",
        "last_name": "Customer",
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
        "status": "draft",
        "payment_status": "pending",
    }
    fields.update(overrides)
    order = Order(**fields)
    session.add(order)
    await session.flush()
    return order


async def _make_staff_with_custom_role(
    db_session: AsyncSession, make_staff_user: MakeStaffUser, *, codes: list[str]
) -> StaffUser:
    staff_user = await make_staff_user(role_code=None)
    role = await _make_role_with_permissions(db_session, codes=codes)
    db_session.add(StaffRole(staff_user_id=staff_user.id, role_id=role.id))
    await db_session.flush()
    return staff_user


# --- Authentication ------------------------------------------------------


async def test_list_offers_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/offers")
    assert response.status_code == 401


# --- offers.view -----------------------------------------------------------


async def test_list_offers_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/offers", headers=_headers(outsider))
    assert response.status_code == 403


async def test_list_offers_succeeds_for_view_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    agent = await make_staff_user(role_code="customer_support_agent")
    response = await authed_client.get("/api/v1/offers", headers=_headers(agent))
    assert response.status_code == 200, response.text


# --- offers.manage -----------------------------------------------------


async def test_create_offer_requires_manage_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    agent = await make_staff_user(role_code="customer_support_agent")
    response = await authed_client.post(
        "/api/v1/offers", json=_offer_payload(), headers=_headers(agent)
    )
    assert response.status_code == 403


async def test_create_offer_succeeds_for_manage_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    marketer = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/offers", json=_offer_payload(), headers=_headers(marketer)
    )
    assert response.status_code == 201, response.text


# --- offers.approve special case on the transition endpoint ------------------


async def test_transition_to_approved_requires_approve_permission_not_just_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    marketer = await make_staff_user(role_code="marketing_manager")
    offer_id = await _create_offer_via_api(authed_client, marketer)

    manage_only = await _make_staff_with_custom_role(
        db_session, make_staff_user, codes=["offers.view", "offers.manage"]
    )

    # offers.manage alone can move draft -> in_review (an ordinary transition)...
    in_review_response = await authed_client.post(
        f"/api/v1/offers/{offer_id}/transition",
        json={"target_status": "in_review"},
        headers=_headers(manage_only),
    )
    assert in_review_response.status_code == 200, in_review_response.text

    # ...but not in_review -> approved, which requires offers.approve specifically.
    approve_response = await authed_client.post(
        f"/api/v1/offers/{offer_id}/transition",
        json={"target_status": "approved"},
        headers=_headers(manage_only),
    )
    assert approve_response.status_code == 403


async def test_transition_to_approved_succeeds_for_role_with_approve_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    marketer = await make_staff_user(role_code="marketing_manager")
    offer_id = await _create_offer_via_api(authed_client, marketer)

    await authed_client.post(
        f"/api/v1/offers/{offer_id}/transition",
        json={"target_status": "in_review"},
        headers=_headers(marketer),
    )
    approve_response = await authed_client.post(
        f"/api/v1/offers/{offer_id}/transition",
        json={"target_status": "approved"},
        headers=_headers(marketer),
    )
    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["data"]["status"] == "approved"


# --- offers.redeem -----------------------------------------------------


async def test_reserve_redemption_requires_redeem_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # marketing_manager owns offer configuration but not day-to-day redemption.
    marketer = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/offers/redemptions/reserve",
        json={
            "offer_id": str(uuid.uuid4()),
            "customer_id": str(uuid.uuid4()),
            "subtotal_minor": 1000,
            "eligible_amount_minor": 1000,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(marketer),
    )
    assert response.status_code == 403


async def test_reserve_redemption_succeeds_for_redeem_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    offer = await offers_service.create_offer(
        db_session,
        actor=owner,
        payload=OfferCreateIn(
            offer_code=f"OFFER-{uuid.uuid4().hex[:10]}",
            internal_name="API redeem offer",
            customer_facing_name="API redeem offer",
            offer_type="percentage_discount",
            initial_version=OfferVersionCreateIn(
                eligibility_rule=_ALWAYS_TRUE_RULE,
                benefit_rule=PercentageBenefit(percent=Decimal("10")),
                valid_from=datetime.now(UTC) - timedelta(days=1),
            ),
        ),
    )
    offer = await offers_service.transition_offer(
        db_session, actor=owner, offer=offer, target_status="in_review"
    )
    offer = await offers_service.transition_offer(
        db_session, actor=owner, offer=offer, target_status="approved"
    )
    offer = await offers_service.transition_offer(
        db_session, actor=owner, offer=offer, target_status="active"
    )

    customer = await _make_customer(db_session)
    agent = await make_staff_user(role_code="customer_support_agent")
    response = await authed_client.post(
        "/api/v1/offers/redemptions/reserve",
        json={
            "offer_id": str(offer.id),
            "customer_id": str(customer.id),
            "subtotal_minor": 1000,
            "eligible_amount_minor": 1000,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(agent),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["status"] == "reserved"


# --- offers.reverse -----------------------------------------------------


async def test_reverse_redemption_requires_dedicated_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # customer_support_agent has offers.redeem but not offers.reverse.
    agent = await make_staff_user(role_code="customer_support_agent")
    response = await authed_client.post(
        f"/api/v1/offers/redemptions/{uuid.uuid4()}/reverse",
        json={"reason": "refund"},
        headers=_headers(agent),
    )
    assert response.status_code == 403


async def test_reverse_redemption_succeeds_for_reverse_role(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    offer = await offers_service.create_offer(
        db_session,
        actor=owner,
        payload=OfferCreateIn(
            offer_code=f"OFFER-{uuid.uuid4().hex[:10]}",
            internal_name="API reverse offer",
            customer_facing_name="API reverse offer",
            offer_type="percentage_discount",
            initial_version=OfferVersionCreateIn(
                eligibility_rule=_ALWAYS_TRUE_RULE,
                benefit_rule=PercentageBenefit(percent=Decimal("10")),
                valid_from=datetime.now(UTC) - timedelta(days=1),
            ),
        ),
    )
    offer = await offers_service.transition_offer(
        db_session, actor=owner, offer=offer, target_status="in_review"
    )
    offer = await offers_service.transition_offer(
        db_session, actor=owner, offer=offer, target_status="approved"
    )
    offer = await offers_service.transition_offer(
        db_session, actor=owner, offer=offer, target_status="active"
    )

    from app.offers import redemptions as redemptions_service

    customer = await _make_customer(db_session)
    redemption = await redemptions_service.reserve(
        db_session,
        offer_id=offer.id,
        customer_id=customer.id,
        coupon_code=None,
        order_id=None,
        order_channel="dine_in",
        order_type="dine_in",
        subtotal_minor=1000,
        product_ids=[],
        category_ids=[],
        eligible_amount_minor=1000,
        idempotency_key=f"idem-{uuid.uuid4().hex}",
        actor=owner,
    )
    order = await _make_order(db_session, customer_id=customer.id)
    confirmed = await redemptions_service.confirm(
        db_session, redemption=redemption, order_id=order.id, actor=owner
    )

    finance = await make_staff_user(role_code="finance_manager")
    response = await authed_client.post(
        f"/api/v1/offers/redemptions/{confirmed.id}/reverse",
        json={"reason": "refund"},
        headers=_headers(finance),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "reversed"


# --- 404 ---------------------------------------------------------------


async def test_get_unknown_offer_returns_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")
    response = await authed_client.get(f"/api/v1/offers/{uuid.uuid4()}", headers=_headers(owner))
    assert response.status_code == 404
