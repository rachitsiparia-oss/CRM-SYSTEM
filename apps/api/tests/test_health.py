import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_request_id_header_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


async def test_unknown_route_returns_stable_error_shape(client: AsyncClient) -> None:
    response = await client.get("/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert "request_id" in body["error"]


async def test_metrics_exposes_prometheus_text_format(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "crm_http_requests_total" in body
    assert "crm_job_queue_depth" in body
    assert "crm_db_pool_size" in body
