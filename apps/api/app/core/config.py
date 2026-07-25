from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration, validated at process startup.

    Required variables have no default and cause startup to fail fast with a
    clear error rather than serving traffic with missing configuration — see
    CLAUDE.md section 21 and DEPLOYMENT_AND_ENV.md section 4.3. Database,
    Redis, and provider credentials are intentionally absent from Phase 1:
    they are added when Phase 2 (Database Foundation) and later phases need
    them, not invented ahead of time.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "rkpr-api"
    environment: Literal["local", "test", "staging", "production"] = "local"

    api_base_url: str = "http://localhost:8000"
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    sentry_dsn: str | None = None
    log_level: Literal["debug", "info", "warning", "error"] = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
