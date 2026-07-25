"""Rate-limit hook for authentication and authorization endpoints —
SECURITY_PERFORMANCE_AND_QUALITY.md section 3.4 ("rate limiting by IP and
account identifier", "progressive delay or lockout controls").

This is an in-process fixed-window limiter, correct for the single API
instance this project currently runs (ROADMAP.md Phase 3/17 — Redis is not
provisioned for `apps/api` until the Phase 17 staging deployment). It is
intentionally isolated behind `check_rate_limit()` so a later phase can
swap in a Redis-backed implementation for multi-instance correctness
without changing any call site.

Actual password verification happens at Supabase Auth, which the browser
calls directly — this backend never receives a password, so Supabase Auth
is the credential-brute-force control (SECURITY_PERFORMANCE_AND_QUALITY.md
section 3.1, "Supabase Auth remains the approved identity source"). This
hook throttles repeated invalid-token and permission-denied requests
against our own API, which Supabase's own rate limiting does not cover.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _Window:
    count: int = 0
    window_started_at: float = field(default_factory=time.monotonic)


class RateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, _Window] = defaultdict(_Window)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Returns True if the call is allowed, False if the limit is
        exceeded for this key within the current window."""
        now = time.monotonic()
        with self._lock:
            window = self._windows[key]
            if now - window.window_started_at > window_seconds:
                window.count = 0
                window.window_started_at = now
            window.count += 1
            allowed = window.count <= limit
        if not allowed:
            logger.warning(
                "rate_limit_exceeded", key=key, limit=limit, window_seconds=window_seconds
            )
        return allowed


_limiter = RateLimiter()


def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    return _limiter.check(key, limit=limit, window_seconds=window_seconds)
