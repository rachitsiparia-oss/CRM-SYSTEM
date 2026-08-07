import uuid

import pytest
from app.cache.client import get_redis_client
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter, check_rate_limit


def _skip_without_redis() -> None:
    if not get_settings().redis_url:
        pytest.skip("REDIS_URL not configured")


def test_allows_calls_within_limit() -> None:
    limiter = RateLimiter()
    for _ in range(5):
        assert limiter.check("k", limit=5, window_seconds=60) is True


def test_blocks_once_limit_exceeded_within_window() -> None:
    limiter = RateLimiter()
    for _ in range(3):
        assert limiter.check("k", limit=3, window_seconds=60) is True
    assert limiter.check("k", limit=3, window_seconds=60) is False


def test_progressive_backoff_extends_penalty_past_the_raw_window() -> None:
    # A key that keeps violating stays blocked well past window_seconds —
    # not just until the fixed window rolls over — because each violation
    # doubles the penalty from the window it happened in.
    limiter = RateLimiter()
    window = limiter._windows["k"]
    for _ in range(3):
        assert limiter.check("k", limit=3, window_seconds=60) is True
    assert limiter.check("k", limit=3, window_seconds=60) is False
    assert window.consecutive_violations == 1
    first_penalty_deadline = window.blocked_until
    assert first_penalty_deadline > window.window_started_at + 60  # penalty outlasts the raw window

    # Still inside the penalty — blocked regardless of the raw window math,
    # and the still-pending penalty is left untouched by this call.
    assert limiter.check("k", limit=3, window_seconds=60) is False
    assert window.blocked_until == first_penalty_deadline

    # Penalty "served" (cleared directly) but still inside the original
    # window — a second violation doubles the penalty again.
    window.blocked_until = 0.0
    assert limiter.check("k", limit=3, window_seconds=60) is False
    assert window.consecutive_violations == 2
    assert window.blocked_until > first_penalty_deadline


def test_clean_window_resets_violation_streak() -> None:
    limiter = RateLimiter()
    window = limiter._windows["k"]
    for _ in range(3):
        assert limiter.check("k", limit=3, window_seconds=60) is True
    assert limiter.check("k", limit=3, window_seconds=60) is False
    assert window.consecutive_violations == 1

    # Serve the penalty and roll into a fresh window — this call becomes
    # that window's first (clean-so-far) request; the streak survives
    # because the window it's replacing was the violating one.
    window.blocked_until = 0.0
    window.window_started_at -= 61
    assert limiter.check("k", limit=3, window_seconds=60) is True
    assert window.consecutive_violations == 1

    # Let that fresh window complete with no further violation — decay is
    # applied on the transition into the window after it.
    window.window_started_at -= 61
    assert limiter.check("k", limit=3, window_seconds=60) is True
    assert window.consecutive_violations == 0


def test_different_keys_are_independent() -> None:
    limiter = RateLimiter()
    for _ in range(3):
        assert limiter.check("a", limit=3, window_seconds=60) is True
    assert limiter.check("a", limit=3, window_seconds=60) is False
    assert limiter.check("b", limit=3, window_seconds=60) is True


async def _cleanup_redis_key(key: str) -> None:
    client = get_redis_client()
    assert client is not None
    from app.core.rate_limit import _redis_keys

    blocked_key, count_key, violations_key = _redis_keys(key)
    await client.delete(blocked_key, count_key, violations_key)


async def test_check_rate_limit_uses_redis_and_allows_within_limit() -> None:
    _skip_without_redis()
    key = f"test-{uuid.uuid4().hex[:8]}"
    try:
        for _ in range(3):
            assert await check_rate_limit(key, limit=3, window_seconds=60) is True
    finally:
        await _cleanup_redis_key(key)


async def test_check_rate_limit_blocks_once_limit_exceeded_via_redis() -> None:
    _skip_without_redis()
    key = f"test-{uuid.uuid4().hex[:8]}"
    try:
        for _ in range(3):
            assert await check_rate_limit(key, limit=3, window_seconds=60) is True
        assert await check_rate_limit(key, limit=3, window_seconds=60) is False
        # Still blocked on a later call within the penalty window, even
        # though the raw fixed window would already have room again.
        assert await check_rate_limit(key, limit=3, window_seconds=60) is False
    finally:
        await _cleanup_redis_key(key)


async def test_check_rate_limit_redis_keys_are_environment_scoped() -> None:
    _skip_without_redis()
    from app.core.rate_limit import _redis_keys

    key = f"test-{uuid.uuid4().hex[:8]}"
    blocked_key, count_key, violations_key = _redis_keys(key)
    environment = get_settings().environment
    assert blocked_key == f"ratelimit:{environment}:{key}:blocked"
    assert count_key == f"ratelimit:{environment}:{key}:count"
    assert violations_key == f"ratelimit:{environment}:{key}:violations"


async def test_check_rate_limit_falls_back_to_in_process_when_redis_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.rate_limit.get_redis_client", lambda: None)
    key = f"test-{uuid.uuid4().hex[:8]}"
    for _ in range(2):
        assert await check_rate_limit(key, limit=2, window_seconds=60) is True
    assert await check_rate_limit(key, limit=2, window_seconds=60) is False
