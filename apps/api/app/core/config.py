from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/app/core/config.py -> parents[2] == apps/api. Resolved from this
# file's own location, not the process's current working directory — a
# relative "env_file" silently reads the wrong .env (or none) depending on
# where the process happens to be launched from.
_API_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment configuration, validated at process startup.

    Required variables have no default and cause startup to fail fast with a
    clear error rather than serving traffic with missing configuration — see
    CLAUDE.md section 21 and DEPLOYMENT_AND_ENV.md section 4.3. Redis and
    provider credentials remain intentionally absent until the phase that
    needs them (Phase 12+, Phase 14, Phase 15) — not invented ahead of time.
    """

    model_config = SettingsConfigDict(
        env_file=_API_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "rkpr-api"
    environment: Literal["local", "test", "staging", "production"] = "local"

    api_base_url: str = "http://localhost:8000"
    # Used only to build the Supabase password-recovery email's redirect
    # link back to the dashboard — not a security boundary (CORS is).
    dashboard_base_url: str = "http://localhost:3000"
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    sentry_dsn: str | None = None
    log_level: Literal["debug", "info", "warning", "error"] = "info"

    # Database — required from Phase 2 onward. Use the Supabase connection
    # pooler (session mode, port 5432), not the direct db.<ref>.supabase.co
    # host: the direct host is IPv6-only on most projects and will time out
    # on networks without IPv6 egress — see apps/api/.env.example.
    database_url: str | None = None
    db_pool_size: int = 5
    db_pool_max_overflow: int = 10
    db_echo: bool = False

    # Phase 16 hardening — CLAUDE.md section 19 ("slow endpoints must be
    # observable"). A structured warning log, not a new metrics backend:
    # narrow instrumentation matching the existing Prometheus-scope
    # philosophy in app/core/metrics.py, not a slow-query dashboard.
    slow_query_threshold_ms: int = 500
    slow_request_threshold_ms: int = 1000

    # Supabase Auth — required from Phase 3 onward. `supabase_service_role_key`
    # is server-only (SECURITY_PERFORMANCE_AND_QUALITY.md section 3.7,
    # section 5.2) and must never be sent to the browser or logged.
    #
    # Supabase projects sign access tokens one of two ways, and
    # app.auth.tokens.decode_access_token supports both by reading the
    # token's own `alg` header: the legacy shared secret (HS256, verified
    # against `auth_jwt_signing_secret`) or the current default, JWT
    # Signing Keys (ES256/RS256, asymmetric, verified via `supabase_url`'s
    # published JWKS endpoint — `auth_jwt_signing_secret` is simply unused
    # for a project on this mode). Both are required below regardless of
    # which mode a given project actually uses, since either could still
    # be needed and there is no cost to having both configured.
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    auth_jwt_signing_secret: str | None = None

    # Controlled AI — Phase 14 (TOOLS.md section 8, GROWTH_AND_INTELLIGENCE.md
    # section 14). OpenAI is the approved primary provider, Groq an optional
    # fallback; neither is required — with both unset, `app.controlled_ai`
    # falls back to a deterministic mock provider so ordinary CRM workflows
    # (and tests) never depend on live AI credentials being configured
    # (CLAUDE.md section 17, "AI outage does not block core CRM").
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # Redis (Upstash) — Phase 15 (TOOLS.md section 6). Cache, not a source
    # of truth; app.cache degrades to a transparent cache-miss whenever
    # this is unset or unreachable rather than failing requests
    # (CLAUDE.md section 21, TOOLS.md section 6's "failure must degrade
    # safely"). The same variable ARQ's worker already uses for its queue
    # transport (apps/worker/worker/config.py) — this is apps/api's own
    # copy for its own connection, a separate service per TOOLS.md 7.1.
    redis_url: str | None = None

    @model_validator(mode="after")
    def _require_database_url_outside_local_dev(self) -> Self:
        # Staging and production must never start without a real database —
        # CLAUDE.md section 21 ("Provide startup validation with helpful
        # errors"). Local and test stay lenient so Phase 1 tooling (which
        # predates the database) keeps working.
        if self.environment in ("staging", "production") and not self.database_url:
            raise ValueError(
                "DATABASE_URL is required when ENVIRONMENT is 'staging' or 'production'"
            )
        return self

    @model_validator(mode="after")
    def _require_auth_config_outside_local_dev(self) -> Self:
        if self.environment in ("staging", "production") and not (
            self.supabase_url and self.supabase_service_role_key and self.auth_jwt_signing_secret
        ):
            raise ValueError(
                "SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and AUTH_JWT_SIGNING_SECRET are "
                "required when ENVIRONMENT is 'staging' or 'production'"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
