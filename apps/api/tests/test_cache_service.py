"""Tests for `app.cache` — the Redis-backed L2 cache layer
(INTEGRATIONS_AUTOMATIONS_REALTIME.md/TOOLS.md section 6). Exercises real
Redis when `REDIS_URL` is configured; skips when it is not, matching this
suite's existing `DATABASE_URL`-not-configured skip convention rather than
mocking the cache away."""

from __future__ import annotations

import uuid

import pytest
from app.cache.keys import build_key, build_prefix
from app.cache.service import delete, get_json, invalidate_prefix, set_json
from app.core.config import get_settings


def _skip_without_redis() -> None:
    if not get_settings().redis_url:
        pytest.skip("REDIS_URL not configured")


async def test_set_and_get_json_round_trips() -> None:
    _skip_without_redis()
    key = build_key("settings", f"test-{uuid.uuid4().hex[:8]}")
    try:
        await set_json(key, {"hello": "world"}, family="settings")
        value = await get_json(key)
        assert value == {"hello": "world"}
    finally:
        await delete(key)


async def test_get_json_miss_returns_none() -> None:
    _skip_without_redis()
    key = build_key("settings", f"test-never-set-{uuid.uuid4().hex[:8]}")
    assert await get_json(key) is None


async def test_delete_removes_the_key() -> None:
    _skip_without_redis()
    key = build_key("settings", f"test-delete-{uuid.uuid4().hex[:8]}")
    await set_json(key, {"a": 1}, family="settings")
    assert await get_json(key) is not None

    await delete(key)
    assert await get_json(key) is None


async def test_invalidate_prefix_removes_every_key_under_the_prefix() -> None:
    _skip_without_redis()
    suffix = uuid.uuid4().hex[:8]
    subprefix = f"test-invalidate-{suffix}"
    key_a = build_key("settings", subprefix, "a")
    key_b = build_key("settings", subprefix, "b")
    await set_json(key_a, {"n": "a"}, family="settings")
    await set_json(key_b, {"n": "b"}, family="settings")

    removed = await invalidate_prefix(build_prefix("settings", subprefix))
    assert removed >= 2
    assert await get_json(key_a) is None
    assert await get_json(key_b) is None
