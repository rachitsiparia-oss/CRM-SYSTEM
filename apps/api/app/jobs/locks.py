"""Postgres session-level advisory locks — the distributed lock primitive
for cron jobs that must not double-run across worker instances. No new
Redis-lock mechanism is introduced (TOOLS.md section 6 permits Redis locks,
but a session-level advisory lock over the same Postgres connection the job
already uses is simpler and needs no additional infrastructure). This
relies on the Supabase Session pooler (not Transaction pooler) assigning a
dedicated backend connection per session — the same reason
DEPLOYMENT_AND_ENV.md already requires Session-mode pooling, so
`pg_try_advisory_lock`/`pg_advisory_unlock` operate on a stable connection
for the lock's lifetime.
"""

import hashlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.errors import LockNotAcquiredError


def _lock_id(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()[:8]
    return int.from_bytes(digest, byteorder="big", signed=True)


@asynccontextmanager
async def advisory_lock(session: AsyncSession, key: str) -> AsyncIterator[None]:
    """Raises `LockNotAcquiredError` immediately if already held elsewhere
    — callers should treat that as "another worker is already running
    this," not as an error to alert on."""
    lock_id = _lock_id(key)
    acquired = bool(
        (await session.execute(text("SELECT pg_try_advisory_lock(:id)"), {"id": lock_id})).scalar()
    )
    if not acquired:
        raise LockNotAcquiredError(f"Could not acquire distributed lock for {key!r}.")
    try:
        yield
    finally:
        await session.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": lock_id})
