from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Process is running. Never exposes secrets or internal configuration
    — CLAUDE.md section 19."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    """Service can accept traffic.

    Phase 1 has no database or Redis dependency yet, so readiness currently
    mirrors liveness. Phase 2 onward adds real dependency checks (database
    connectivity) here without exposing connection strings or credentials.
    """
    return {"status": "ok"}
