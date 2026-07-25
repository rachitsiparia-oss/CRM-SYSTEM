from app.core.config import Settings


def configure_sentry(settings: Settings) -> None:
    """Initializes Sentry only when a real DSN is configured. Optional
    providers must remain disabled without crashing unrelated modules —
    CLAUDE.md section 21. A `replace_me...` placeholder left in `.env` (the
    normal state before Sentry is actually wired up) is not a valid DSN URL
    and must not crash application startup — treat anything that isn't an
    http(s) URL as "not configured" rather than attempting to initialize."""
    dsn = settings.sentry_dsn
    if not dsn or not dsn.startswith(("http://", "https://")):
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        send_default_pii=False,
    )
