import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


def _skip_without_database() -> None:
    from app.core.config import get_settings

    if not get_settings().database_url:
        pytest.skip("DATABASE_URL not configured")


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
    # crm_db_pool_size (and the job-queue/dead-letter gauges) are computed
    # from a real database query at scrape time — this test genuinely needs
    # a real DATABASE_URL, unlike the other /health/* tests here.
    _skip_without_database()
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "crm_http_requests_total" in body
    assert "crm_job_queue_depth" in body
    assert "crm_db_pool_size" in body


async def test_security_headers_present_on_every_response(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers["permissions-policy"]
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )


async def test_hsts_absent_outside_staging_and_production(client: AsyncClient) -> None:
    # The test fixture's app runs with environment="test" (see
    # app.core.config.Settings' default) — HSTS on a non-HTTPS-guaranteed
    # environment would be misleading, so it must be absent here.
    response = await client.get("/health/live")
    assert "strict-transport-security" not in response.headers


async def test_interactive_docs_disabled_outside_local_and_test(client: AsyncClient) -> None:
    # Confirms the docs_enabled gate exists and openapi_url stays wired for
    # the test environment itself (docs_enabled includes "test") — the
    # staging/production disablement is exercised by
    # test_docs_disabled_in_production below via a dedicated app instance.
    response = await client.get("/openapi.json")
    assert response.status_code == 200


async def test_slow_request_logs_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.main import create_app

    class _RecordingLogger:
        def __init__(self) -> None:
            self.warnings: list[dict[str, object]] = []

        def warning(self, event: str, **kwargs: object) -> None:
            self.warnings.append({"event": event, **kwargs})

    recorder = _RecordingLogger()
    monkeypatch.setattr("app.core.metrics_middleware.logger", recorder)
    # A very small but non-zero threshold: 0 disables the check entirely
    # (matching app.core.slow_query's identical "0 means off" semantic),
    # and any real request through the ASGI transport takes over 1ms.
    monkeypatch.setenv("SLOW_REQUEST_THRESHOLD_MS", "1")
    get_settings.cache_clear()
    try:
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            response = await ac.get("/health/live")
        assert response.status_code == 200
    finally:
        get_settings.cache_clear()

    assert len(recorder.warnings) == 1
    assert recorder.warnings[0]["event"] == "slow_request"
    assert recorder.warnings[0]["route"] == "/health/live"
    assert recorder.warnings[0]["status"] == 200


async def test_lifespan_disposes_engine_on_shutdown_when_database_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import AsyncMock

    from app.core.config import Settings
    from app.main import _lifespan_factory

    # A directly-constructed Settings, not get_settings() + real env vars —
    # this test only cares that dispose() is called when database_url is
    # truthy (the engine itself is mocked below), so it must not depend on
    # a real DATABASE_URL existing in the test environment (CI has none —
    # see test_lifespan_skips_disposal_when_database_not_configured below
    # for the same pattern on the opposite branch).
    settings = Settings(database_url="postgresql+psycopg://test:test@localhost:5432/test")

    disposed = AsyncMock()

    class _FakeEngine:
        dispose = disposed

    monkeypatch.setattr("app.main.get_engine", lambda: _FakeEngine())

    lifespan = _lifespan_factory(settings)
    async with lifespan(object()):  # type: ignore[arg-type]
        pass

    disposed.assert_awaited_once()


async def test_lifespan_skips_disposal_when_database_not_configured() -> None:
    from app.core.config import Settings
    from app.main import _lifespan_factory

    settings = Settings(database_url=None)
    lifespan = _lifespan_factory(settings)
    # Must not raise even though no engine was ever created.
    async with lifespan(object()):  # type: ignore[arg-type]
        pass


async def test_docs_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings
    from app.main import create_app

    # A directly-constructed Settings monkeypatched onto app.main.get_settings,
    # not real env vars — this test only cares about the docs_enabled gate,
    # not real DB/Supabase connectivity, so it must not depend on a real
    # DATABASE_URL/SUPABASE_URL/etc existing in the test environment (CI has
    # none of these; only local dev's own .env file happened to mask this).
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://test:test@localhost:5432/test",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="test-service-role-key",
        auth_jwt_signing_secret="test-signing-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    app = create_app()
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
