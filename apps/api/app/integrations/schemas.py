from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class IntegrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    category: str
    provider_code: str
    display_name: str
    status: str
    environment: str
    is_enabled: bool
    config_version: int
    credential_reference: str | None
    credential_last_validated_at: datetime | None
    webhook_configured: bool
    base_endpoint: str | None
    default_sender: str | None
    rate_limit_config: dict[str, Any] | None
    timeout_seconds: int
    retry_policy_reference: str | None
    capability_flags: dict[str, Any] | None
    health_state: str
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_error_category: str | None
    created_at: datetime
    updated_at: datetime


class HealthCheckSummaryOut(BaseModel):
    healthy: int
    unhealthy: int
