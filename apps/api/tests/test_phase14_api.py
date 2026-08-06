"""HTTP-layer authentication/authorization tests for the Phase 14 routers
(analytics/dashboard, reports, exports, report-schedules, anomalies,
forecasts, controlled AI). Service-layer workflow correctness is covered
by the dedicated test_reports_service.py/test_anomalies.py/
test_forecasts.py/test_controlled_ai.py files.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from app.db.models import StaffUser
from httpx import AsyncClient

from tests.conftest import make_access_token

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _headers(staff_user: StaffUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_access_token(staff_user.auth_user_id)}"}


# --- Analytics metrics catalog and dashboards --------------------------------


async def test_list_metrics_requires_authentication(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/analytics/metrics")
    assert response.status_code == 401


async def test_list_metrics_scopes_to_caller_permissions(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="hr_manager")
    response = await authed_client.get("/api/v1/analytics/metrics", headers=_headers(actor))
    assert response.status_code == 200
    codes = {m["code"] for m in response.json()["data"]}
    # hr_manager holds analytics.staff.view but not analytics.sales.view.
    assert "staff_active_count" in codes
    assert "sales_completed_order_count" not in codes


async def test_get_dashboard_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/dashboard/executive", headers=_headers(outsider))
    assert response.status_code == 403


async def test_get_dashboard_unknown_domain_is_404(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    response = await authed_client.get(
        "/api/v1/dashboard/not_a_real_domain", headers=_headers(actor)
    )
    assert response.status_code == 404


async def test_get_dashboard_succeeds_for_owner(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    response = await authed_client.get("/api/v1/dashboard/executive", headers=_headers(actor))
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["domain"] == "executive"
    assert len(body["metrics"]) == 5


# --- Report definitions -------------------------------------------------------


async def test_create_report_definition_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.post(
        "/api/v1/reports/definitions",
        headers=_headers(outsider),
        json={
            "name": "Unauthorized report",
            "domain": "executive",
            "metric_codes": ["exec_net_sales"],
        },
    )
    assert response.status_code == 403


async def test_create_and_run_report_definition_end_to_end(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    create_response = await authed_client.post(
        "/api/v1/reports/definitions",
        headers=_headers(actor),
        json={
            "name": "API test report",
            "domain": "executive",
            "metric_codes": ["exec_net_sales", "exec_completed_orders"],
        },
    )
    assert create_response.status_code == 201
    definition_id = create_response.json()["data"]["id"]

    run_response = await authed_client.post(
        f"/api/v1/reports/definitions/{definition_id}/run",
        headers=_headers(actor),
        json={"window_code": "current_month"},
    )
    assert run_response.status_code == 202
    body = run_response.json()["data"]
    assert body["run"]["status"] == "completed"
    assert len(body["metrics"]) == 2


# --- Anomaly rules and findings ------------------------------------------------


async def test_list_anomaly_rules_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/anomalies/rules", headers=_headers(outsider))
    assert response.status_code == 403


async def test_list_anomaly_rules_succeeds_for_owner(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    response = await authed_client.get("/api/v1/anomalies/rules", headers=_headers(actor))
    assert response.status_code == 200


# --- Forecast definitions -------------------------------------------------------


async def test_list_forecast_definitions_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/forecasts/definitions", headers=_headers(outsider))
    assert response.status_code == 403


async def test_list_forecast_definitions_succeeds_for_owner(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    response = await authed_client.get("/api/v1/forecasts/definitions", headers=_headers(actor))
    assert response.status_code == 200


# --- Controlled AI -------------------------------------------------------------


async def test_create_ai_request_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.post(
        "/api/v1/ai/requests",
        headers=_headers(outsider),
        json={"feature_code": "dashboard_summary", "params": {"domain": "executive"}},
    )
    assert response.status_code == 403


async def test_create_ai_request_nl_query_plan_requires_query_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    # hr_manager holds ai.analytics.use but not ai.analytics.query.
    actor = await make_staff_user(role_code="hr_manager")
    response = await authed_client.post(
        "/api/v1/ai/requests",
        headers=_headers(actor),
        json={"feature_code": "nl_question_query_plan", "params": {"question": "How are sales?"}},
    )
    assert response.status_code == 403


async def test_get_ai_request_forbidden_for_non_requester(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    other = await make_staff_user(role_code="owner")
    create_response = await authed_client.post(
        "/api/v1/ai/requests",
        headers=_headers(actor),
        json={
            "feature_code": "dashboard_summary",
            "params": {"domain": "executive", "window_code": "current_month"},
        },
    )
    assert create_response.status_code == 201
    request_id = create_response.json()["data"]["id"]

    get_response = await authed_client.get(
        f"/api/v1/ai/requests/{request_id}", headers=_headers(other)
    )
    assert get_response.status_code == 403


async def test_create_ai_request_is_rate_limited_per_staff_account(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    from app.controlled_ai.router import _AI_REQUEST_LIMIT

    actor = await make_staff_user(role_code="owner")
    payload = {
        "feature_code": "dashboard_summary",
        "params": {"domain": "executive", "window_code": "current_month"},
    }
    for _ in range(_AI_REQUEST_LIMIT):
        response = await authed_client.post(
            "/api/v1/ai/requests", headers=_headers(actor), json=payload
        )
        assert response.status_code == 201

    over_limit = await authed_client.post(
        "/api/v1/ai/requests", headers=_headers(actor), json=payload
    )
    assert over_limit.status_code == 429


# --- Scheduled reports -----------------------------------------------------------


async def test_list_report_schedules_requires_permission(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    outsider = await make_staff_user(role_code=None)
    response = await authed_client.get("/api/v1/report-schedules", headers=_headers(outsider))
    assert response.status_code == 403


async def test_list_report_schedules_succeeds_for_owner(
    authed_client: AsyncClient, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    response = await authed_client.get("/api/v1/report-schedules", headers=_headers(actor))
    assert response.status_code == 200
