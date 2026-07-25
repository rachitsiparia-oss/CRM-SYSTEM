"""Regression coverage for the invitation email bug: create_invitation
used to only write a StaffInvitation bookkeeping row and never actually
told Supabase to email anyone. httpx.AsyncClient.post is mocked here so
these tests never send a real email or depend on network access.
"""

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.db.models import StaffUser
from app.staff.service import create_invitation
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _mock_response(status_code: int) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    return response


async def test_create_invitation_calls_supabase_invite_endpoint(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")

    with patch(
        "httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_response(200))
    ) as mock_post:
        invitation = await create_invitation(
            db_session,
            actor=owner,
            email="new-hire@example.test",
            first_name="New",
            last_name="Hire",
            department_id=None,
            role_code="kitchen_staff",
            request=None,
        )

    assert invitation.status == "pending"
    assert invitation.email == "new-hire@example.test"
    mock_post.assert_awaited_once()
    call = mock_post.await_args
    assert call is not None
    assert call.args[0].endswith("/auth/v1/invite")
    assert call.kwargs["json"]["email"] == "new-hire@example.test"
    assert "redirect_to" in call.kwargs["params"]


async def test_create_invitation_fails_when_supabase_rejects_email(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")

    with (
        patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_response(422))),
        pytest.raises(HTTPException) as exc_info,
    ):
        await create_invitation(
            db_session,
            actor=owner,
            email="already-registered@example.test",
            first_name="Someone",
            last_name=None,
            department_id=None,
            role_code="kitchen_staff",
            request=None,
        )

    assert exc_info.value.status_code == 409


async def test_create_invitation_fails_when_supabase_is_unreachable(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    owner = await make_staff_user(role_code="owner")

    with (
        patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("boom"))),
        pytest.raises(HTTPException) as exc_info,
    ):
        await create_invitation(
            db_session,
            actor=owner,
            email="unreachable@example.test",
            first_name="Someone",
            last_name=None,
            department_id=None,
            role_code="kitchen_staff",
            request=None,
        )

    assert exc_info.value.status_code == 502
