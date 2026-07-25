from app.core.config import Settings


def configure_sentry(settings: Settings) -> None:
    """Initializes Sentry only when a DSN is configured. Optional providers
    must remain disabled without crashing unrelated modules — CLAUDE.md
    section 21."""
    if not settings.sentry_dsn:
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        send_default_pii=False,
    )
