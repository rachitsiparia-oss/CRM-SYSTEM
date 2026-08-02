from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperationalSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    maintenance_mode_enabled: bool
    maintenance_message: str | None
    scheduler_enabled: bool
    default_max_attempts: int
    default_retry_backoff_seconds: int
    default_retry_backoff_cap_seconds: int
    worker_max_jobs: int
    worker_job_timeout_seconds: int
    queue_priority_config: dict[str, Any] | None
    notification_channel_config: dict[str, Any] | None
    active_ai_provider_code: str | None
    version: int
    updated_at: datetime


class OperationalSettingsUpdateIn(BaseModel):
    maintenance_mode_enabled: bool | None = None
    maintenance_message: str | None = Field(default=None, max_length=2000)
    scheduler_enabled: bool | None = None
    default_max_attempts: int | None = Field(default=None, gt=0)
    default_retry_backoff_seconds: int | None = Field(default=None, gt=0)
    default_retry_backoff_cap_seconds: int | None = Field(default=None, gt=0)
    worker_max_jobs: int | None = Field(default=None, gt=0)
    worker_job_timeout_seconds: int | None = Field(default=None, gt=0)
    queue_priority_config: dict[str, Any] | None = None
    notification_channel_config: dict[str, Any] | None = None
    active_ai_provider_code: str | None = Field(default=None, max_length=32)
