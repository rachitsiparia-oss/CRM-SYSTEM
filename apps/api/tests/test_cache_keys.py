"""Unit tests for `app.cache.keys` — no Redis needed, since this module
only builds strings. Phase 17 added an environment segment so local,
staging, and production entries never collide when they share one
physical Upstash instance (DEPLOYMENT_AND_ENV.md section 14.2)."""

from __future__ import annotations

import pytest
from app.cache.keys import build_key, build_prefix
from app.core.config import get_settings


def test_build_key_includes_current_environment() -> None:
    environment = get_settings().environment
    key = build_key("settings", "example")
    assert key == f"crm:{environment}:v1:settings:example"


def test_build_prefix_without_parts_includes_current_environment() -> None:
    environment = get_settings().environment
    prefix = build_prefix("settings")
    assert prefix == f"crm:{environment}:v1:settings"


def test_different_environments_produce_different_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    # A directly-constructed Settings monkeypatched onto app.cache.keys'
    # own get_settings reference, not a real ENVIRONMENT env var — the
    # staging/production branch of Settings' validator requires a real
    # DATABASE_URL/SUPABASE_*/etc, which only local dev's own .env file
    # happened to supply; CI has none of these (see test_health.py's
    # test_docs_disabled_in_production for the same pattern).
    from app.core.config import Settings

    settings = Settings(
        environment="staging",
        database_url="postgresql+psycopg://test:test@localhost:5432/test",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="test-service-role-key",
        auth_jwt_signing_secret="test-signing-secret",
    )
    monkeypatch.setattr("app.cache.keys.get_settings", lambda: settings)
    staging_key = build_key("settings", "example")
    assert staging_key == "crm:staging:v1:settings:example"
