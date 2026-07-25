from typing import Any

from arq import cron
from arq.connections import RedisSettings

from worker.asyncio_policy import configure_event_loop_policy
from worker.config import get_worker_settings
from worker.logging import configure_logging, get_logger
from worker.observability import configure_sentry
from worker.tasks.heartbeat import heartbeat

# Must run before ARQ creates its event loop — see worker/asyncio_policy.py.
configure_event_loop_policy()

settings = get_worker_settings()
configure_logging(settings)
configure_sentry(settings)
logger = get_logger(__name__)


async def on_startup(ctx: dict[str, Any]) -> None:
    logger.info("worker_startup", environment=settings.environment)


async def on_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker_shutdown", environment=settings.environment)


class WorkerSettings:
    """ARQ worker entry point. Business jobs (order notifications, reminders,
    reports, campaigns, etc.) are registered here as they are implemented in
    their scheduled roadmap phase — see INTEGRATIONS_AUTOMATIONS_REALTIME.md
    section 14 for the approved automation catalog."""

    functions = [heartbeat]
    cron_jobs = [cron(heartbeat, minute=set(range(0, 60, 15)))]
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_jobs = settings.max_jobs
    job_timeout = settings.job_timeout_seconds
    redis_settings = (
        RedisSettings.from_dsn(settings.redis_url) if settings.redis_url else RedisSettings()
    )
