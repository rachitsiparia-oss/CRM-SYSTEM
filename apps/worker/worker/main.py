from typing import Any

from arq import cron
from arq.connections import RedisSettings

from worker.asyncio_policy import configure_event_loop_policy
from worker.config import get_worker_settings
from worker.db import get_engine
from worker.logging import configure_logging, get_logger
from worker.observability import configure_sentry
from worker.tasks.anomalies_and_recovery import (
    evaluate_anomalies,
    process_review_requests,
    run_complaint_sla_escalations,
)
from worker.tasks.communications import process_scheduled_messages, retry_failed_messages
from worker.tasks.event_bus import dispatch_communication_events, dispatch_outbox_events
from worker.tasks.heartbeat import heartbeat
from worker.tasks.inventory import send_low_stock_alerts
from worker.tasks.loyalty_gift_cards import expire_gift_cards, expire_loyalty_points
from worker.tasks.maintenance import purge_stale_records
from worker.tasks.notifications import dispatch_notification_deliveries
from worker.tasks.reports import run_forecasts, run_scheduled_reports
from worker.tasks.reservations import expire_waitlist, send_reservation_reminders
from worker.tasks.segments_campaigns import refresh_segments, sync_campaigns
from worker.tasks.staff_reminders import (
    send_certification_expiry_reminders,
    send_knowledge_acknowledgement_reminders,
    send_training_overdue_reminders,
)

# Must run before ARQ creates its event loop — see worker/asyncio_policy.py.
configure_event_loop_policy()

settings = get_worker_settings()
configure_logging(settings)
configure_sentry(settings)
logger = get_logger(__name__)


async def on_startup(ctx: dict[str, Any]) -> None:
    logger.info("worker_startup", environment=settings.environment)


async def on_shutdown(ctx: dict[str, Any]) -> None:
    # Cleanly close every pooled connection rather than leaving them for the
    # OS to reap on process exit — same reasoning as apps/api's identical
    # lifespan-shutdown fix (CLAUDE.md section 11). Only attempted when a
    # database is actually configured.
    if get_worker_settings().database_url:
        await get_engine().dispose()
    logger.info("worker_shutdown", environment=settings.environment)


class WorkerSettings:
    """ARQ worker entry point — INTEGRATIONS_AUTOMATIONS_REALTIME.md section
    14's approved automation catalog, activated. Every cadence below is a
    cron tick, not a queue-routing decision: ARQ itself runs a single job
    queue per worker process (there is no native per-`queue_name` routing),
    so `queue_name` on each task is purely the `JobRecord` reporting
    dimension the future Queue Dashboard (Phase 15 frontend) groups by.
    Each cron entry's own function is also registered in `functions`,
    making it directly enqueueable on demand (e.g. a future "Run now"
    action) rather than only cron-triggered.

    Overlap safety when apps/worker is scaled beyond one replica is handled
    inside `worker.scheduling.run_scheduled_job`, not here — see its
    docstring. Cadences are UTC wall-clock (ARQ has no timezone concept);
    the once-daily jobs are placed in the RKPR restaurant's late-night
    UTC window (~00:30-03:00 IST) to avoid the lunch/dinner rush.
    """

    functions = [
        heartbeat,
        dispatch_outbox_events,
        dispatch_communication_events,
        process_scheduled_messages,
        retry_failed_messages,
        dispatch_notification_deliveries,
        run_complaint_sla_escalations,
        send_reservation_reminders,
        expire_waitlist,
        sync_campaigns,
        send_low_stock_alerts,
        run_scheduled_reports,
        process_review_requests,
        evaluate_anomalies,
        run_forecasts,
        expire_loyalty_points,
        expire_gift_cards,
        refresh_segments,
        send_certification_expiry_reminders,
        send_training_overdue_reminders,
        send_knowledge_acknowledgement_reminders,
        purge_stale_records,
    ]
    cron_jobs = [
        cron(heartbeat, minute=set(range(0, 60, 15))),
        # Near-real-time dispatch — every 2 minutes.
        cron(dispatch_outbox_events, minute=set(range(0, 60, 2))),
        cron(dispatch_communication_events, minute=set(range(0, 60, 2))),
        cron(process_scheduled_messages, minute=set(range(0, 60, 2))),
        cron(dispatch_notification_deliveries, minute=set(range(1, 60, 3))),
        # Operational SLAs — every 5 minutes.
        cron(run_complaint_sla_escalations, minute=set(range(0, 60, 5))),
        cron(send_reservation_reminders, minute=set(range(0, 60, 5))),
        cron(expire_waitlist, minute=set(range(2, 60, 5))),
        # Retry/reconciliation sweeps — every 10 minutes.
        cron(retry_failed_messages, minute=set(range(0, 60, 10))),
        cron(sync_campaigns, minute=set(range(4, 60, 10))),
        # Periodic checks — every 15-30 minutes.
        cron(run_scheduled_reports, minute=set(range(0, 60, 15))),
        cron(send_low_stock_alerts, minute=set(range(6, 60, 30))),
        # Hourly.
        cron(process_review_requests, minute={10}),
        cron(evaluate_anomalies, minute={20}, hour=set(range(0, 24, 6))),
        # Once-daily, off-peak UTC.
        cron(run_forecasts, hour={20}, minute={0}),
        cron(expire_loyalty_points, hour={19}, minute={0}),
        cron(expire_gift_cards, hour={19}, minute={10}),
        cron(refresh_segments, hour={18}, minute={0}),
        cron(send_certification_expiry_reminders, hour={3}, minute={0}),
        cron(send_training_overdue_reminders, hour={3}, minute={10}),
        cron(send_knowledge_acknowledgement_reminders, hour={3}, minute={20}),
        cron(purge_stale_records, hour={21}, minute={30}),
    ]
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_jobs = settings.max_jobs
    job_timeout = settings.job_timeout_seconds
    # Environment-scoped so local/staging/production never share a queue
    # when they share one physical Upstash instance (DEPLOYMENT_AND_ENV.md
    # section 27, "no shared staging and production queue") — Phase 17
    # reused the existing Redis instance across environments rather than
    # provisioning a separate one per environment (see
    # docs/phase-17/DEPLOYMENT_REPORT.md), so this is the actual isolation
    # boundary rather than a formality.
    queue_name = f"arq:queue:{settings.environment}"
    redis_settings = (
        RedisSettings.from_dsn(settings.redis_url) if settings.redis_url else RedisSettings()
    )
