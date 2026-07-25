from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.db.session import check_database_connection

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
