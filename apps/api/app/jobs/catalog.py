"""Static description of every cron entry registered in
`apps/worker/worker/main.py`. This is documentation for the Monitoring
Dashboard's Scheduler view, not the scheduling authority — apps/api and
apps/worker are separately deployed processes (TOOLS.md section 7.1), so
apps/api cannot introspect the worker's live ARQ registration. Keep this
in sync by hand whenever `WorkerSettings.cron_jobs` changes; a mismatch
here is a documentation bug, not a scheduling bug — the worker's own
`cron_jobs` list is what actually runs.
"""

from typing import NamedTuple


class ScheduledJobCatalogEntry(NamedTuple):
    job_type: str
    queue_name: str
    cadence: str
    description: str


SCHEDULED_JOB_CATALOG: tuple[ScheduledJobCatalogEntry, ...] = (
    ScheduledJobCatalogEntry(
        "event_bus.dispatch_pending", "critical-domain", "every 2 minutes", "Outbox event fan-out."
    ),
    ScheduledJobCatalogEntry(
        "communications.dispatch_events",
        "communications",
        "every 2 minutes",
        "Reservation/order communication event consumer.",
    ),
    ScheduledJobCatalogEntry(
        "communications.process_scheduled_messages",
        "communications",
        "every 2 minutes",
        "Sends due scheduled messages.",
    ),
    ScheduledJobCatalogEntry(
        "notifications.dispatch_pending_deliveries",
        "communications",
        "every 3 minutes",
        "Delivers pending email/WhatsApp/SMS notification channels.",
    ),
    ScheduledJobCatalogEntry(
        "complaints.run_sla_escalations",
        "critical-domain",
        "every 5 minutes",
        "Detects SLA breaches and auto-escalates.",
    ),
    ScheduledJobCatalogEntry(
        "reservations.dispatch_reminders",
        "communications",
        "every 5 minutes",
        "Sends due reservation reminders.",
    ),
    ScheduledJobCatalogEntry(
        "reservations.expire_waitlist",
        "critical-domain",
        "every 5 minutes",
        "Expires stale waitlist entries.",
    ),
    ScheduledJobCatalogEntry(
        "communications.retry_failed_messages",
        "communications",
        "every 10 minutes",
        "Retries retryable failed outbound messages.",
    ),
    ScheduledJobCatalogEntry(
        "campaigns.sync_running",
        "campaigns",
        "every 10 minutes",
        "Syncs recipient delivery status for running campaigns.",
    ),
    ScheduledJobCatalogEntry(
        "report_schedules.run_due", "reports", "every 15 minutes", "Runs due scheduled reports."
    ),
    ScheduledJobCatalogEntry(
        "inventory.low_stock_alerts",
        "critical-domain",
        "every 30 minutes",
        "Sends low-stock alerts to inventory managers.",
    ),
    ScheduledJobCatalogEntry(
        "feedback.process_review_requests",
        "communications",
        "hourly",
        "Evaluates eligibility and expires stale review requests.",
    ),
    ScheduledJobCatalogEntry(
        "anomalies.evaluate_all_active",
        "reports",
        "every 6 hours",
        "Evaluates active anomaly rules against fresh metrics.",
    ),
    ScheduledJobCatalogEntry(
        "forecasts.run_all_active", "reports", "daily", "Regenerates active forecast snapshots."
    ),
    ScheduledJobCatalogEntry(
        "loyalty.expire_due_points", "campaigns", "daily", "Expires due loyalty ledger points."
    ),
    ScheduledJobCatalogEntry(
        "gift_cards.expire_due", "campaigns", "daily", "Expires gift cards past their expiry date."
    ),
    ScheduledJobCatalogEntry(
        "segments.refresh_all_dynamic",
        "campaigns",
        "daily",
        "Recomputes dynamic segment membership.",
    ),
    ScheduledJobCatalogEntry(
        "staff.certification_expiry_reminders",
        "communications",
        "daily",
        "Reminds staff of expiring certifications.",
    ),
    ScheduledJobCatalogEntry(
        "staff.training_overdue_reminders",
        "communications",
        "daily",
        "Reminds staff of overdue training assignments.",
    ),
    ScheduledJobCatalogEntry(
        "knowledge.acknowledgement_reminders",
        "communications",
        "daily",
        "Reminds staff of overdue knowledge acknowledgements.",
    ),
    ScheduledJobCatalogEntry(
        "maintenance.purge_stale_records",
        "maintenance",
        "daily",
        "Purges terminal JobRecord/OutboxEvent rows past their retention window.",
    ),
)
