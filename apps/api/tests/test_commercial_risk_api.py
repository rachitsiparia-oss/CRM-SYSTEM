"""HTTP-layer permission tests for the commercial-risk router —
`commercial_risk.view` / `commercial_risk.review`.

`operations_manager` holds `commercial_risk.view` but not
`commercial_risk.review` in the seeded role matrix (app/permissions/
role_matrix.py) — used here to prove the review endpoint needs its own,
separate permission rather than falling back to view access.
`finance_manager` holds both, per the same matrix's "finance owns every
ledger reversal and risk review" comment.
"""

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.commercial_risk import service
from app.db.models import CommercialRiskFlag, StaffUser
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


async def _make_flag(db_session: AsyncSession) -> CommercialRiskFlag:
    return await service.raise_flag(
        db_session, flag_type="repeated_reversal", summary="Repeated reversal detected."
    )


# --- commercial_risk.view --------------------------------------------------


async def test_list_flags_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/commercial-risk/flags")
    assert response.status_code == 401


async def test_list_flags_requires_commercial_risk_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)  # no role, no permissions at all
    response = await authed_client.get("/api/v1/commercial-risk/flags", headers=_headers(outsider))
    assert response.status_code == 403


async def test_list_flags_succeeds_for_operations_manager(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.get("/api/v1/commercial-risk/flags", headers=_headers(viewer))
    assert response.status_code == 200


async def test_get_flag_requires_commercial_risk_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    flag = await _make_flag(db_session)
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get(
        f"/api/v1/commercial-risk/flags/{flag.id}", headers=_headers(outsider)
    )
    assert response.status_code == 403


async def test_get_unknown_flag_returns_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    viewer = await make_staff_user(role_code="operations_manager")
    response = await authed_client.get(
        f"/api/v1/commercial-risk/flags/{uuid.uuid4()}", headers=_headers(viewer)
    )
    assert response.status_code == 404


# --- commercial_risk.review -------------------------------------------------


async def test_review_flag_requires_commercial_risk_review_not_just_view(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    flag = await _make_flag(db_session)
    # operations_manager has commercial_risk.view but not commercial_risk.review.
    viewer_only = await make_staff_user(role_code="operations_manager")
    response = await authed_client.post(
        f"/api/v1/commercial-risk/flags/{flag.id}/review",
        json={"target_status": "resolved"},
        headers=_headers(viewer_only),
    )
    assert response.status_code == 403


async def test_review_flag_succeeds_for_finance_manager(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    flag = await _make_flag(db_session)
    reviewer = await make_staff_user(role_code="finance_manager")
    response = await authed_client.post(
        f"/api/v1/commercial-risk/flags/{flag.id}/review",
        json={"target_status": "reviewing", "resolution_note": "Looking into it."},
        headers=_headers(reviewer),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "reviewing"
    assert data["reviewed_by"] == str(reviewer.id)


async def test_review_flag_rejects_invalid_transition(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser, db_session: AsyncSession
) -> None:
    flag = await _make_flag(db_session)
    reviewer = await make_staff_user(role_code="finance_manager")
    resolved_response = await authed_client.post(
        f"/api/v1/commercial-risk/flags/{flag.id}/review",
        json={"target_status": "resolved"},
        headers=_headers(reviewer),
    )
    assert resolved_response.status_code == 200

    response = await authed_client.post(
        f"/api/v1/commercial-risk/flags/{flag.id}/review",
        json={"target_status": "dismissed"},
        headers=_headers(reviewer),
    )
    assert response.status_code == 400
