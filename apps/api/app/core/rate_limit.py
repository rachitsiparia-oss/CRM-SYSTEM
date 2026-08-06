"""Rate-limit hook for authentication and authorization endpoints —
SECURITY_PERFORMANCE_AND_QUALITY.md section 3.4 ("rate limiting by IP and
account identifier", "progressive delay or lockout controls").

This is an in-process fixed-window limiter, correct for the single API
instance this project currently runs. Phase 15 provisioned a Redis client
for `apps/api` (`app.cache`) for caching, but this limiter has not been
migrated onto it — a rate-limit counter has different correctness
requirements (atomic increment-and-check, not a get/set-with-TTL cache
read) than `app.cache`'s generic helpers provide, so that migration is
left for the Phase 17 staging deployment rather than folded in here. It is
intentionally isolated behind `check_rate_limit()` so that later migration
can swap in a Redis-backed implementation for multi-instance correctness
without changing any call site.

Actual password verification happens at Supabase Auth, which the browser
calls directly — this backend never receives a password, so Supabase Auth
is the credential-brute-force control (SECURITY_PERFORMANCE_AND_QUALITY.md
section 3.1, "Supabase Auth remains the approved identity source"). This
hook throttles repeated invalid-token and permission-denied requests
against our own API, which Supabase's own rate limiting does not cover.

Phase 16 hardening added progressive backoff: a key that keeps tripping the
limit is blocked for an exponentially growing penalty window instead of
being let back in the instant the fixed window rolls over — a scripted
retry loop timed to the window boundary no longer gets a fresh attempt
every `window_seconds`. A key earns back a clean slate (penalty resets)
once it completes a full window without a violation.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_PENALTY_SECONDS = 3600.0


@dataclass
class _Window:
    count: int = 0
    window_started_at: float = field(default_factory=time.monotonic)
    consecutive_violations: int = 0
    blocked_until: float = 0.0


class RateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, _Window] = defaultdict(_Window)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Returns True if the call is allowed, False if the limit is
        exceeded for this key within the current window or the key is still
        serving a progressive-backoff penalty from a prior violation."""
        now = time.monotonic()
        with self._lock:
            window = self._windows[key]
            if now < window.blocked_until:
                allowed = False
            else:
                if now - window.window_started_at > window_seconds:
                    if window.count <= limit:
                        window.consecutive_violations = 0
                    window.count = 0
                    window.window_started_at = now
                window.count += 1
                allowed = window.count <= limit
                if not allowed:
                    window.consecutive_violations += 1
                    penalty = min(
                        window_seconds * (2**window.consecutive_violations),
                        _MAX_PENALTY_SECONDS,
                    )
                    window.blocked_until = now + penalty
        if not allowed:
            logger.warning(
                "rate_limit_exceeded", key=key, limit=limit, window_seconds=window_seconds
            )
        return allowed


_limiter = RateLimiter()


def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    return _limiter.check(key, limit=limit, window_seconds=window_seconds)
