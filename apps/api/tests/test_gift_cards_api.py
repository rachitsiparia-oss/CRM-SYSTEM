"""HTTP-layer tests for the gift card router — authentication and
authorization, plus the reveal-endpoint response-shape guarantee (never
returns the full plaintext code). Ledger/lifecycle correctness is covered
by `test_gift_cards_ledger.py`.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


def _issue_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "initial_amount_minor": 5000,
        "idempotency_key": f"idem-{uuid.uuid4().hex}",
    }
    payload.update(overrides)
    return payload


async def _issue_and_activate(
    authed_client: AsyncClient, issuer: StaffUser, **overrides: Any
) -> tuple[str, str]:
    """Returns (gift_card_id, plaintext_code)."""
    issue_resp = await authed_client.post(
        "/api/v1/gift-cards", json=_issue_payload(**overrides), headers=_headers(issuer)
    )
    assert issue_resp.status_code == 201, issue_resp.text
    body = issue_resp.json()["data"]
    card_id = body["gift_card"]["id"]
    code = body["code"]

    activate_resp = await authed_client.post(
        f"/api/v1/gift-cards/{card_id}/activate", headers=_headers(issuer)
    )
    assert activate_resp.status_code == 200, activate_resp.text
    return card_id, code


# --- Authentication and authorization ----------------------------------------


async def test_list_gift_cards_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/gift-cards")
    assert response.status_code == 401


async def test_list_gift_cards_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/gift-cards", headers=_headers(outsider))
    assert response.status_code == 403


async def test_issue_requires_gift_cards_issue(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # marketing_manager has gift_cards.view/.manage but not .issue.
    manager = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/gift-cards", json=_issue_payload(), headers=_headers(manager)
    )
    assert response.status_code == 403


async def test_issue_succeeds_for_finance_manager(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    response = await authed_client.post(
        "/api/v1/gift-cards", json=_issue_payload(), headers=_headers(finance)
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["gift_card"]["status"] == "draft"
    assert len(data["code"]) > 0


async def test_redeem_requires_gift_cards_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    _card_id, code = await _issue_and_activate(authed_client, finance)

    # operations_manager only has gift_cards.view, not .manage.
    view_only = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        "/api/v1/gift-cards/redeem",
        json={
            "code": code,
            "amount_minor": 500,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(view_only),
    )
    assert response.status_code == 403


async def test_redeem_succeeds_for_gift_cards_manage(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    _card_id, code = await _issue_and_activate(authed_client, finance)

    # marketing_manager has gift_cards.manage.
    manager = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/gift-cards/redeem",
        json={
            "code": code,
            "amount_minor": 500,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(manager),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["amount_delta_minor"] == -500


async def test_reveal_requires_gift_cards_reveal_sensitive(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    card_id, _code = await _issue_and_activate(authed_client, finance)

    # marketing_manager does not have gift_cards.reveal_sensitive.
    manager = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.get(
        f"/api/v1/gift-cards/{card_id}/reveal", headers=_headers(manager)
    )
    assert response.status_code == 403


async def test_reveal_succeeds_and_never_returns_the_full_code(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    card_id, plaintext_code = await _issue_and_activate(authed_client, finance)

    response = await authed_client.get(
        f"/api/v1/gift-cards/{card_id}/reveal", headers=_headers(finance)
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert set(data.keys()) == {"card_number", "code_last4"}
    assert len(data["code_last4"]) == 4
    assert data["code_last4"] == plaintext_code[-4:]
    # The full plaintext code must never appear anywhere in the response.
    assert plaintext_code not in response.text


async def test_adjust_requires_gift_cards_adjust(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    card_id, _code = await _issue_and_activate(authed_client, finance)

    manager = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        f"/api/v1/gift-cards/{card_id}/adjust",
        json={
            "amount_delta_minor": 100,
            "reason": "goodwill",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(manager),
    )
    assert response.status_code == 403


async def test_adjust_succeeds_for_gift_cards_adjust(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    card_id, _code = await _issue_and_activate(authed_client, finance)

    response = await authed_client.post(
        f"/api/v1/gift-cards/{card_id}/adjust",
        json={
            "amount_delta_minor": 100,
            "reason": "goodwill",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(finance),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["amount_delta_minor"] == 100


async def test_reverse_requires_gift_cards_reverse(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    _card_id, code = await _issue_and_activate(authed_client, finance)
    redeem_resp = await authed_client.post(
        "/api/v1/gift-cards/redeem",
        json={
            "code": code,
            "amount_minor": 500,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(finance),
    )
    entry_id = redeem_resp.json()["data"]["id"]

    # marketing_manager has gift_cards.manage but not .reverse.
    manager = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        "/api/v1/gift-cards/reverse",
        json={
            "entry_id": entry_id,
            "reason": "mistake",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(manager),
    )
    assert response.status_code == 403


async def test_reverse_succeeds_for_gift_cards_reverse(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    finance = await make_staff_user(role_code="finance_manager")
    _card_id, code = await _issue_and_activate(authed_client, finance)
    redeem_resp = await authed_client.post(
        "/api/v1/gift-cards/redeem",
        json={
            "code": code,
            "amount_minor": 500,
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(finance),
    )
    entry_id = redeem_resp.json()["data"]["id"]

    response = await authed_client.post(
        "/api/v1/gift-cards/reverse",
        json={
            "entry_id": entry_id,
            "reason": "mistake",
            "idempotency_key": f"idem-{uuid.uuid4().hex}",
        },
        headers=_headers(finance),
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["amount_delta_minor"] == 500


async def test_analytics_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/gift-cards/analytics", headers=_headers(outsider))
    assert response.status_code == 403

    finance = await make_staff_user(role_code="finance_manager")
    response = await authed_client.get("/api/v1/gift-cards/analytics", headers=_headers(finance))
    assert response.status_code == 200
