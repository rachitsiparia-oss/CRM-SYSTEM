"""Generic get/set/invalidate helpers over `app.cache.client`. Every
function here swallows Redis errors and returns a cache-miss/no-op instead
of raising — a Redis outage must never turn into an API 500
(INTEGRATIONS_AUTOMATIONS_REALTIME.md section 2.6, "failure isolation").
Callers pass already-JSON-safe dicts/lists; this module does not know
about domain shapes.
"""

import json
from typing import Any

from app.cache.client import get_redis_client
from app.cache.keys import CACHE_TTL_SECONDS
from app.core.logging import get_logger
from app.core.metrics import cache_hits_total, cache_misses_total

logger = get_logger(__name__)


def _family_from_key(key: str) -> str:
    # Keys are "crm:v1:{family}:{parts}" — see app.cache.keys.build_key.
    parts = key.split(":")
    return parts[2] if len(parts) > 2 else "unknown"


async def get_json(key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        return None
    family = _family_from_key(key)
    try:
        raw = await client.get(key)
    except Exception:
        logger.warning("cache_get_failed", key=key)
        cache_misses_total.labels(family=family).inc()
        return None
    if raw is None:
        cache_misses_total.labels(family=family).inc()
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        logger.warning("cache_value_corrupt", key=key)
        cache_misses_total.labels(family=family).inc()
        return None
    cache_hits_total.labels(family=family).inc()
    return value


async def set_json(key: str, value: Any, *, family: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    ttl = CACHE_TTL_SECONDS[family]
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        logger.warning("cache_set_failed", key=key)


async def delete(key: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        await client.delete(key)
    except Exception:
        logger.warning("cache_delete_failed", key=key)


async def invalidate_prefix(prefix: str) -> int:
    """Bulk-invalidates every key under `prefix` via non-blocking `SCAN` —
    never `KEYS`, which blocks the whole Redis instance
    (TOOLS.md section 6's rules apply even to housekeeping operations).
    Returns the number of keys removed; 0 (not an error) if Redis is
    unavailable."""
    client = get_redis_client()
    if client is None:
        return 0
    removed = 0
    try:
        async for key in client.scan_iter(match=f"{prefix}*", count=100):
            await client.delete(key)
            removed += 1
    except Exception:
        logger.warning("cache_invalidate_prefix_failed", prefix=prefix)
    return removed
