from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Environment configuration for the ARQ worker, validated at startup.

    No Redis or database credentials are required to exist yet in Phase 1 —
    the worker validates configuration shape and fails safely if it is later
    asked to run without required values, per CLAUDE.md section 21.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    redis_url: str | None = None
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    max_jobs: int = 10
    job_timeout_seconds: int = 300


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
