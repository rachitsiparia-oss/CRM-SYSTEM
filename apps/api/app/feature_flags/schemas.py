from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class FeatureFlagCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_.]+$")
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    is_enabled: bool = False


class SetFlagEnabledIn(BaseModel):
    is_enabled: bool
