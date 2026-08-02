from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OutboxEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    aggregate_type: str
    aggregate_id: uuid.UUID
    payload: dict[str, Any]
    status: str
    available_at: datetime
    attempts: int
    locked_by: str | None
    locked_at: datetime | None
    completed_at: datetime | None
    last_error: str | None
    idempotency_key: str | None
    created_at: datetime
