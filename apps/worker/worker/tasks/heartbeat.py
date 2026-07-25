from typing import Any

from worker.logging import get_logger

logger = get_logger(__name__)


async def heartbeat(ctx: dict[str, Any]) -> str:
    """Foundation-only scheduled job proving the ARQ scheduler wiring works.

    This is intentionally not a business job — CLAUDE.md section 14 requires
    every real job to define trigger, idempotency, retries, and audit
    behavior; those land with the modules that actually need them, starting
    in later phases.
    """
    logger.info("worker_heartbeat")
    return "ok"
