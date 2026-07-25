from worker.config import WorkerSettings


def configure_sentry(settings: WorkerSettings) -> None:
    """Initializes Sentry only when a real DSN is configured — mirrors
    apps/api/app/core/observability.py. A `replace_me...` placeholder left
    in `.env` must not crash worker startup."""
    dsn = settings.sentry_dsn
    if not dsn or not dsn.startswith(("http://", "https://")):
        return

    import sentry_sdk

    sentry_sdk.init(dsn=dsn, environment=settings.environment, send_default_pii=False)
