"""Unit tests for `app.cache.keys` — no Redis needed, since this module
only builds strings. Phase 17 added an environment segment so local,
staging, and production entries never collide when they share one
physical Upstash instance (DEPLOYMENT_AND_ENV.md section 14.2)."""

from __future__ import annotations

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


def test_different_environments_produce_different_keys(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    get_settings.cache_clear()
    try:
        staging_key = build_key("settings", "example")
        assert staging_key == "crm:staging:v1:settings:example"
    finally:
        get_settings.cache_clear()
