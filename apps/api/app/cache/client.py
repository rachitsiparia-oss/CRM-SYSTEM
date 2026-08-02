"""The Redis client used by `app.cache` — TOOLS.md section 6 (Upstash
Redis). Never the source of truth: PostgreSQL remains authoritative for
every value this module ever caches. `get_redis_client()` returns `None`
when `REDIS_URL` is unset rather than raising, so every caller degrades to
"treat this as a cache miss" instead of failing the request — CLAUDE.md
section 21 and TOOLS.md section 6's "failure must degrade safely."
"""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> Redis | None:
    settings = get_settings()
    if not settings.redis_url:
        return None
    client: Redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    return client
