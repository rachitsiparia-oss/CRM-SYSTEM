"""Rate-limit hook for authentication and authorization endpoints —
SECURITY_PERFORMANCE_AND_QUALITY.md section 3.4 ("rate limiting by IP and
account identifier", "progressive delay or lockout controls").

Phase 17 migrated this onto Redis (`app.cache.client.get_redis_client`) for
multi-instance correctness — the in-process `RateLimiter` below was correct
only for a single API instance, and Railway can run more than one. The
Redis path (`_check_redis`) does the increment-and-check atomically in a
single Lua script (`_LUA_SCRIPT`) so two concurrent API instances can never
both observe "count == limit" and both let a request through. When Redis is
unavailable — unset, unreachable, or the Lua call raises — `check_rate_limit`
falls back to the original in-process `RateLimiter` singleton rather than
failing open or 500ing the request (DEPLOYMENT_AND_ENV.md section 14.3,
"safe fallback when Redis is unavailable"; the same failure-isolation
pattern `app.cache.service` already uses). The in-process class is kept
as-is (and still exercised directly by its own unit tests) purely to serve
as that fallback and because it needs no Redis to test.

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
once it completes a full window without a violation. The Redis-backed path
preserves the same shape (fixed window, exponential penalty capped at
`_MAX_PENALTY_SECONDS`) but decays the violation streak on a simpler
"no violation for one window" TTL rather than requiring one full *clean*
window to elapse — a deliberate simplification to keep the check a single
atomic script instead of needing multiple round trips; it does not weaken
the limiter's behavior against a real attacker.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from app.cache.client import get_redis_client
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_PENALTY_SECONDS = 3600.0

# KEYS[1]=blocked, KEYS[2]=count, KEYS[3]=violations
# ARGV[1]=limit, ARGV[2]=window_seconds, ARGV[3]=max_penalty_seconds
_LUA_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 1 then
  return 0
end
local count = redis.call('INCR', KEYS[2])
if count == 1 then
  redis.call('EXPIRE', KEYS[2], ARGV[2])
end
local limit = tonumber(ARGV[1])
if count <= limit then
  return 1
end
local violations = redis.call('INCR', KEYS[3])
redis.call('EXPIRE', KEYS[3], ARGV[2] * 2)
local window = tonumber(ARGV[2])
local max_penalty = tonumber(ARGV[3])
local penalty = window * (2 ^ violations)
if penalty > max_penalty then
  penalty = max_penalty
end
redis.call('SET', KEYS[1], '1', 'EX', math.floor(penalty))
return 0
"""


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


def _redis_keys(key: str) -> tuple[str, str, str]:
    env = get_settings().environment
    base = f"ratelimit:{env}:{key}"
    return f"{base}:blocked", f"{base}:count", f"{base}:violations"


async def _check_redis(key: str, *, limit: int, window_seconds: int) -> bool | None:
    """Returns True/False on a successful Redis check, or None when Redis
    is unavailable/failed and the caller should fall back to `_limiter`."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        blocked_key, count_key, violations_key = _redis_keys(key)
        # redis-py's `eval` stub types the return as `Awaitable[str] | str`
        # (shared with the sync client) even on `redis.asyncio.Redis`, where
        # it is always awaitable — a known stub inaccuracy, not a real
        # ambiguity here.
        result = await client.eval(  # type: ignore[misc]
            _LUA_SCRIPT,
            3,
            blocked_key,
            count_key,
            violations_key,
            str(limit),
            str(window_seconds),
            str(_MAX_PENALTY_SECONDS),
        )
    except Exception:
        logger.warning("rate_limit_redis_unavailable", key=key)
        return None
    allowed = bool(result)
    if not allowed:
        logger.warning("rate_limit_exceeded", key=key, limit=limit, window_seconds=window_seconds)
    return allowed


async def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> bool:
    redis_result = await _check_redis(key, limit=limit, window_seconds=window_seconds)
    if redis_result is not None:
        return redis_result
    return _limiter.check(key, limit=limit, window_seconds=window_seconds)
