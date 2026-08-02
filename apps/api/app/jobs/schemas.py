from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    trigger: str
    queue_name: str
    priority: str
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: datetime | None
    timeout_seconds: int
    correlation_id: str | None
    idempotency_key: str | None
    progress: str | None
    result: dict[str, Any] | None
    failure_category: str | None
    failure_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class QueueStatOut(BaseModel):
    queue_name: str
    status: str
    count: int


class SchedulerCatalogEntryOut(BaseModel):
    job_type: str
    queue_name: str
    cadence: str
    description: str


class SchedulerStatusOut(BaseModel):
    scheduler_enabled: bool
    jobs: list[SchedulerCatalogEntryOut]


class SchedulerUpdateIn(BaseModel):
    scheduler_enabled: bool
