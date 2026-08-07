import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import jwt
import pytest
from app.cache.service import invalidate_prefix
from app.core.asyncio_policy import configure_event_loop_policy
from app.core.config import get_settings
from app.core.rate_limit import _limiter as _auth_rate_limiter
from app.db.models import Role, StaffRole, StaffUser
from app.db.session import get_db
from app.main import create_app
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must run before pytest-asyncio creates its event loop — see
# app/core/asyncio_policy.py.
configure_event_loop_policy()


@pytest.fixture(autouse=True)
async def _reset_auth_rate_limiter() -> None:
    """`check_rate_limit` tries the Redis-backed limiter first (Phase 17)
    and only falls back to the in-process `_limiter` singleton — module-
    level, shared by the whole process — when Redis is unavailable. Both
    persist across every test in a single pytest run: a test file that
    legitimately makes many authenticated requests (any API test suite
    covering more than a couple of endpoints) can trip the
    requests-per-window bucket purely from test-suite volume, failing with
    429s that have nothing to do with the behavior under test. Clearing
    both before each test is test-isolation hygiene, not a change to the
    limiter's real behavior. This was caught by a full-suite run
    (`docs/phase-17/DEPLOYMENT_REPORT.md`) after the Redis migration —
    with only `_windows.clear()` here, real Redis state kept accumulating
    across the whole run and cascaded into unrelated test failures."""
    _auth_rate_limiter._windows.clear()
    await invalidate_prefix(f"ratelimit:{get_settings().environment}:")


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


@pytest.fixture
async def authed_app(db_session: AsyncSession) -> AsyncIterator[FastAPI]:
    """A FastAPI app whose `get_db` dependency is overridden to the same
    SAVEPOINT-wrapped `db_session`, so requests made against it and direct
    fixture setup share one transaction that always rolls back — no
    permanent writes, real end-to-end authorization enforcement (no mocked
    permission checks).
    """

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def authed_client(authed_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=authed_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


def make_access_token(auth_user_id: uuid.UUID, email: str | None = None) -> str:
    """Mints a real HS256 token signed with the same
    `AUTH_JWT_SIGNING_SECRET` the API verifies against, shaped like a
    genuine Supabase access token — this exercises the real verification
    code path in `app.auth.tokens`, not a mocked one."""
    settings = get_settings()
    assert settings.auth_jwt_signing_secret, "AUTH_JWT_SIGNING_SECRET must be set to run auth tests"
    now = int(time.time())
    payload = {
        "sub": str(auth_user_id),
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "session_id": str(uuid.uuid4()),
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, settings.auth_jwt_signing_secret, algorithm="HS256")


@pytest.fixture
def make_staff_user(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[StaffUser]]:
    """Factory fixture: creates a fully-formed, DB-backed StaffUser (with an
    optional role) inside the test's own SAVEPOINT, with a fresh random
    identity every call so process-global caches (the effective-permissions
    cache) never collide across tests."""

    async def _make(
        *,
        role_code: str | None = None,
        account_status: str = "active",
    ) -> StaffUser:
        suffix = uuid.uuid4().hex[:10]
        staff_user = StaffUser(
            id=uuid.uuid4(),
            auth_user_id=uuid.uuid4(),
            employee_code=f"TEST-{suffix}",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            email=f"test-{suffix}@example.test",
            account_status=account_status,
            employment_status="full_time",
        )
        db_session.add(staff_user)
        await db_session.flush()

        if role_code:
            role_id = await db_session.scalar(select(Role.id).where(Role.code == role_code))
            assert role_id is not None, f"Role {role_code!r} was not found — was it seeded?"
            db_session.add(
                StaffRole(
                    staff_user_id=staff_user.id,
                    role_id=role_id,
                    assigned_at=datetime.now(UTC),
                )
            )
            await db_session.flush()

        return staff_user

    return _make
