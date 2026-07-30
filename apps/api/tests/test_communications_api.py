import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import CommunicationChannel, MessageTemplate, StaffUser
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _whatsapp_channel_id(db_session: AsyncSession) -> str:
    channel_id = await db_session.scalar(
        select(CommunicationChannel.id).where(CommunicationChannel.code == "whatsapp")
    )
    assert channel_id is not None
    return str(channel_id)


async def _create_conversation(
    authed_client: AsyncClient, staff_user: StaffUser, channel_id: str, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"channel_id": channel_id, "phone_e164": "+919812345678"}
    payload.update(overrides)
    response = await authed_client.post(
        "/api/v1/communications/conversations", json=payload, headers=_headers(staff_user)
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()["data"]
    return result


# --- Conversations -----------------------------------------------------------


async def test_create_conversation_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    channel_id = await _whatsapp_channel_id(db_session)
    response = await authed_client.post(
        "/api/v1/communications/conversations",
        json={"channel_id": channel_id},
        headers=_headers(staff_user),
    )
    assert response.status_code == 403


async def test_create_conversation_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, staff_user, channel_id)
    assert conversation["status"] == "open"
    assert conversation["assigned_staff_id"] == str(staff_user.id)


async def test_reply_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    creator = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, creator, channel_id)

    outsider = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/messages",
        json={"body_text": "Hello!", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(outsider),
    )
    assert response.status_code == 403


async def test_reply_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, staff_user, channel_id)

    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/messages",
        json={"body_text": "Hello, how can we help?", "idempotency_key": str(uuid.uuid4())},
        headers=_headers(staff_user),
    )
    assert response.status_code == 201, response.text
    message = response.json()["data"]
    assert message["direction"] == "outbound"
    assert message["delivery_status"] == "sent"


async def test_internal_note_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    creator = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, creator, channel_id)

    outsider = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/notes",
        json={"body_text": "Internal-only context."},
        headers=_headers(outsider),
    )
    assert response.status_code == 403


async def test_internal_note_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, staff_user, channel_id)

    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/notes",
        json={"body_text": "Internal-only context."},
        headers=_headers(staff_user),
    )
    assert response.status_code == 201, response.text
    note = response.json()["data"]
    assert note["direction"] == "internal"
    assert note["message_type"] == "internal_note"
    assert note["recipient_reference"] is None


async def test_resolve_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, staff_user, channel_id)

    no_resolve_role = await make_staff_user(role_code="kitchen_staff")
    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/transition",
        json={"target_status": "resolved"},
        headers=_headers(no_resolve_role),
    )
    assert response.status_code == 403


async def test_resolve_happy_path(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, staff_user, channel_id)

    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/transition",
        json={"target_status": "resolved"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "resolved"


async def test_invalid_transition_is_rejected(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, staff_user, channel_id)

    # open -> closed is not a valid direct transition (must resolve first).
    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/transition",
        json={"target_status": "closed"},
        headers=_headers(staff_user),
    )
    assert response.status_code == 409


async def test_assign_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    channel_id = await _whatsapp_channel_id(db_session)
    conversation = await _create_conversation(authed_client, staff_user, channel_id)

    no_assign_role = await make_staff_user(role_code="marketing_manager")
    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/assign",
        json={"assignee_id": str(staff_user.id)},
        headers=_headers(no_assign_role),
    )
    assert response.status_code == 403


# --- Templates ---------------------------------------------------------------


async def test_template_preview_renders_variables(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    staff_user = await make_staff_user(role_code="operations_manager")
    template_id = await db_session.scalar(
        select(MessageTemplate.id).where(MessageTemplate.code == "reservation_confirmation")
    )
    assert template_id is not None

    response = await authed_client.post(
        f"/api/v1/communications/templates/{template_id}/preview",
        json={
            "variables": {
                "customer_name": "Ananya",
                "party_size": "4",
                "reservation_date": "2026-08-10",
                "reservation_time": "19:00",
                "reservation_number": "RES-TEST1234",
            }
        },
        headers=_headers(staff_user),
    )
    assert response.status_code == 200, response.text
    assert "Ananya" in response.json()["data"]["body"]


# --- Suppression pre-send eligibility -----------------------------------------


async def test_suppressed_destination_blocks_send(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    owner = await make_staff_user(role_code="owner")
    channel_id = await _whatsapp_channel_id(db_session)
    phone = f"+9198{uuid.uuid4().int % 10**8:08d}"

    suppress_response = await authed_client.post(
        "/api/v1/communications/suppressions",
        json={"destination_type": "phone", "destination_value": phone, "reason": "manual_block"},
        headers=_headers(owner),
    )
    assert suppress_response.status_code == 201, suppress_response.text

    conversation = await _create_conversation(authed_client, owner, channel_id, phone_e164=phone)
    response = await authed_client.post(
        f"/api/v1/communications/conversations/{conversation['id']}/messages",
        json={
            "body_text": "This should be suppressed.",
            "recipient_reference": phone,
            "idempotency_key": str(uuid.uuid4()),
        },
        headers=_headers(owner),
    )
    assert response.status_code == 201, response.text
    message = response.json()["data"]
    assert message["delivery_status"] == "suppressed"


# --- Unauthenticated ----------------------------------------------------------


async def test_inbox_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/communications/inbox")
    assert response.status_code == 401
