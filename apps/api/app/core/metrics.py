"""Prometheus metrics — deliberately narrow scope: this instruments the
API process itself (request latency/count, cache hit/miss, DB pool
pressure) and exposes them, plus a handful of *derived* gauges computed at
scrape time from durable Postgres tables (`job_records`, `outbox_events`,
`dead_letter_entries`, `notification_delivery_attempts`, `integrations`).

This is intentionally not a full Prometheus/Grafana/Datadog deployment —
TOOLS.md forbids that "without demonstrated need and approval." The Phase
15 spec explicitly asked for Prometheus-format metrics endpoints, which is
read here as exactly that approval, scoped narrowly to instrumentation
(the `prometheus_client` library and a `/metrics` text endpoint) — no
Prometheus server, scraper, or dashboard is deployed as part of this
project.

apps/worker never gets its own `/metrics` HTTP endpoint: it is a
background ARQ process with no web framework, and adding one solely to
expose metrics would be a second framework for the same concern (CLAUDE.md
section 20). Instead, every worker job's outcome is already durably
recorded in `JobRecord` (via `app.jobs.runner.run_job`); the gauges below
read that table, so worker-side job/queue metrics surface through this
same, single `/metrics` endpoint without any new cross-process transport.
"""

from datetime import UTC, datetime, timedelta

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DeadLetterEntry,
    Integration,
    JobRecord,
    NotificationDeliveryAttempt,
    OutboxEvent,
)

REGISTRY = CollectorRegistry()

http_request_duration_seconds = Histogram(
    "crm_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route", "status"],
    registry=REGISTRY,
)
http_requests_total = Counter(
    "crm_http_requests_total",
    "HTTP requests handled",
    ["method", "route", "status"],
    registry=REGISTRY,
)
cache_hits_total = Counter("crm_cache_hits_total", "Cache read hits", ["family"], registry=REGISTRY)
cache_misses_total = Counter(
    "crm_cache_misses_total", "Cache read misses", ["family"], registry=REGISTRY
)
db_pool_checked_out = Gauge(
    "crm_db_pool_checked_out", "SQLAlchemy connections currently checked out", registry=REGISTRY
)
db_pool_size = Gauge("crm_db_pool_size", "SQLAlchemy pool configured size", registry=REGISTRY)

job_queue_depth = Gauge(
    "crm_job_queue_depth", "JobRecord rows by status", ["status"], registry=REGISTRY
)
job_duration_seconds_avg = Gauge(
    "crm_job_duration_seconds_avg",
    "Average JobRecord duration in the last hour, by job_type",
    ["job_type"],
    registry=REGISTRY,
)
job_retry_attempts_total = Gauge(
    "crm_job_retry_attempts_total",
    "Sum of (attempts - 1) across JobRecord rows completed in the last 24h",
    registry=REGISTRY,
)
outbox_event_depth = Gauge(
    "crm_outbox_event_depth", "OutboxEvent rows by status", ["status"], registry=REGISTRY
)
dead_letter_open_total = Gauge(
    "crm_dead_letter_open_total",
    "DeadLetterEntry rows not yet resolved (new, investigating, or replay_ready)",
    registry=REGISTRY,
)
notification_delivery_pending_total = Gauge(
    "crm_notification_delivery_pending_total",
    "NotificationDeliveryAttempt rows still pending",
    registry=REGISTRY,
)
integration_health_status = Gauge(
    "crm_integration_health_status",
    "1 if an enabled integration's last recorded health check was healthy, else 0",
    ["code"],
    registry=REGISTRY,
)


async def refresh_derived_gauges(session: AsyncSession) -> None:
    """Recomputes every scrape-time gauge from Postgres. Called once per
    `/metrics` request — cheap, bounded, indexed-column aggregate queries
    only; never a full-table scan."""
    job_counts = (
        await session.execute(select(JobRecord.status, func.count()).group_by(JobRecord.status))
    ).all()
    job_queue_depth.clear()
    for status, count in job_counts:
        job_queue_depth.labels(status=status).set(count)

    now = datetime.now(UTC)
    hour_ago = now - timedelta(hours=1)
    duration_rows = (
        await session.execute(
            select(
                JobRecord.job_type,
                func.avg(func.extract("epoch", JobRecord.completed_at - JobRecord.started_at)),
            )
            .where(
                JobRecord.completed_at.is_not(None),
                JobRecord.started_at.is_not(None),
                JobRecord.completed_at >= hour_ago,
            )
            .group_by(JobRecord.job_type)
        )
    ).all()
    job_duration_seconds_avg.clear()
    for job_type, avg_seconds in duration_rows:
        job_duration_seconds_avg.labels(job_type=job_type).set(float(avg_seconds or 0))

    day_ago = now - timedelta(hours=24)
    retry_total = await session.scalar(
        select(func.coalesce(func.sum(JobRecord.attempts - 1), 0)).where(
            JobRecord.completed_at.is_not(None), JobRecord.completed_at >= day_ago
        )
    )
    job_retry_attempts_total.set(retry_total or 0)

    outbox_counts = (
        await session.execute(select(OutboxEvent.status, func.count()).group_by(OutboxEvent.status))
    ).all()
    outbox_event_depth.clear()
    for status, count in outbox_counts:
        outbox_event_depth.labels(status=status).set(count)

    dead_letter_open = await session.scalar(
        select(func.count()).where(
            DeadLetterEntry.resolution_status.in_(("new", "investigating", "replay_ready"))
        )
    )
    dead_letter_open_total.set(dead_letter_open or 0)

    notification_pending = await session.scalar(
        select(func.count()).where(NotificationDeliveryAttempt.status == "pending")
    )
    notification_delivery_pending_total.set(notification_pending or 0)

    integration_rows = (
        await session.execute(
            select(Integration.code, Integration.health_state).where(
                Integration.is_enabled.is_(True)
            )
        )
    ).all()
    integration_health_status.clear()
    for code, health_state in integration_rows:
        integration_health_status.labels(code=code).set(1 if health_state == "healthy" else 0)
