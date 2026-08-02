from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeadLetterEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    original_type: str
    payload_reference: dict[str, Any] | None
    correlation_id: str | None
    failure_category: str | None
    final_error_summary: str | None
    attempt_history: list[dict[str, Any]] | None
    dead_letter_at: datetime
    owner_staff_id: uuid.UUID | None
    resolution_status: str
    replay_eligible: bool
    replay_actor_id: uuid.UUID | None
    replay_at: datetime | None
    notes: str | None
    created_at: datetime


class MarkReplayReadyIn(BaseModel):
    notes: str | None = Field(default=None, max_length=4000)


class IgnoreEntryIn(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)
