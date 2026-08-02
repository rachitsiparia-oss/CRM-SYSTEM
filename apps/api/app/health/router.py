from typing import cast

from fastapi import APIRouter, Depends, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings
from app.core.metrics import REGISTRY, db_pool_checked_out, db_pool_size, refresh_derived_gauges
from app.db.session import check_database_connection, get_db, get_engine

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Process is running. Never exposes secrets or internal configuration
    — CLAUDE.md section 19."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict[str, str]:
    """Service can accept traffic.

    Checks database connectivity when DATABASE_URL is configured — never
    exposes the connection string, host, or credentials, only a boolean
    outcome. Environments that intentionally have no database yet (local/
    test without DATABASE_URL — see core/config.py) stay "ok" rather than
    being reported as degraded for a dependency they were never given.
    """
    settings = get_settings()
    if not settings.database_url:
        return {"status": "ok"}

    if await check_database_connection(settings):
        return {"status": "ok"}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "reason": "database_unreachable"}


@router.get("/metrics")
async def metrics(session: AsyncSession = Depends(get_db)) -> Response:
    """Prometheus exposition format — see `app.core.metrics` for scope and
    the TOOLS.md deviation this narrowly resolves. Unauthenticated, like
    the other `/health/*` endpoints: the values exposed are aggregate
    counts and durations, never customer/staff PII or secrets, and a
    scraper cannot perform an interactive staff login."""
    settings = get_settings()
    if settings.database_url:
        await refresh_derived_gauges(session)
        # create_async_engine's default pool implementation is
        # AsyncAdaptedQueuePool, a QueuePool subclass — checkedout()/size()
        # are QueuePool-specific, not on the base Pool type SQLAlchemy's
        # stubs expose via `.pool`.
        pool = cast(QueuePool, get_engine().pool)
        db_pool_checked_out.set(pool.checkedout())
        db_pool_size.set(pool.size())

    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
