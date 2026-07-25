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


@lru_cache
def get_settings() -> Settings:
    return Settings()
