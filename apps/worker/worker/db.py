"""The worker's own database session factory — deliberately separate from
`app.db.session.get_engine()` (apps/api), even though both bind the same
SQLAlchemy models via the `rkpr-api` workspace dependency. Each is a
separately deployed Railway service (TOOLS.md section 7.1) with its own
`DATABASE_URL` and connection pool sized for its own workload; sharing a
session factory would tie the worker's DB connections to whichever `.env`
apps/api's config module happens to resolve, which is the wrong contract
for a genuinely separate service.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from worker.config import get_worker_settings


class WorkerDatabaseNotConfiguredError(RuntimeError):
    """Raised when a job needs the database but DATABASE_URL is unset —
    matches apps/api's DatabaseNotConfiguredError fail-safely-only-when-used
    behavior (CLAUDE.md section 21)."""


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_worker_settings()
    if not settings.database_url:
        raise WorkerDatabaseNotConfiguredError(
            "DATABASE_URL is not set. Configure it in apps/worker/.env before "
            "running any database-backed job."
        )
    return create_async_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """One transaction per job execution: commits on clean exit, rolls back
    on any exception, always closes — the same contract as apps/api's
    `get_db()` request-scoped session, applied to a job instead of a
    request."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
