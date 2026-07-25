from collections.abc import AsyncIterator

import pytest
from app.core.asyncio_policy import configure_event_loop_policy
from app.core.config import get_settings
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must run before pytest-asyncio creates its event loop — see
# app/core/asyncio_policy.py.
configure_event_loop_policy()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A session bound to a SAVEPOINT that is always rolled back — tests can
    freely insert/violate constraints against the real database without
    leaving any data behind. Skips (rather than fails) when DATABASE_URL is
    not configured, so this suite stays green in environments that
    intentionally have no database yet — CLAUDE.md section 21.
    """
    settings = get_settings()
    if not settings.database_url:
        pytest.skip("DATABASE_URL not configured")

    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        outer_transaction = await conn.begin()
        session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with session_factory() as session:
            yield session
        await outer_transaction.rollback()
    await engine.dispose()
