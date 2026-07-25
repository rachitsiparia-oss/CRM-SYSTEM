from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when database access is attempted without DATABASE_URL set.

    Deliberately not raised at import time — CLAUDE.md section 21 requires
    optional/unconfigured dependencies to fail with a clear error only when
    actually used, not to crash unrelated modules (health checks, non-DB
    routes) at startup.
    """


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    if not settings.database_url:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL is not set. Configure it in apps/api/.env before "
            "using any database-backed endpoint or job."
        )
    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_max_overflow,
        echo=settings.db_echo,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session.

    One transaction per request: commits on clean exit, rolls back on any
    exception, and always closes — CLAUDE.md section 11 ("use transactions
    for operations that must succeed or fail together").
    """
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


async def check_database_connection(settings: Settings) -> bool:
    """Used by the readiness endpoint. Returns False rather than raising so
    a database outage marks the API degraded without crashing the health
    check itself."""
    if not settings.database_url:
        return False
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        return True
    except Exception:
        return False
