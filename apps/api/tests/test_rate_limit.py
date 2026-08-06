from app.core.rate_limit import RateLimiter


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
