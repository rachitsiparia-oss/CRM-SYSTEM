from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FlagType = Literal[
    "repeated_manual_adjustment",
    "repeated_reversal",
    "excessive_coupon_failures",
    "high_value_issuance",
    "self_referral_attempt",
    "identity_overlap",
    "duplicate_attempt",
]
FlagStatus = Literal["open", "reviewing", "resolved", "dismissed"]


class RaiseFlagIn(BaseModel):
    flag_type: FlagType
    customer_id: uuid.UUID | None = None
    staff_user_id: uuid.UUID | None = None
    related_type: str | None = Field(default=None, max_length=40)
    related_id: uuid.UUID | None = None
    summary: str = Field(min_length=1)
    detail: dict[str, object] | None = None


class ReviewFlagIn(BaseModel):
    target_status: Literal["reviewing", "resolved", "dismissed"]
    resolution_note: str | None = None


class FlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    flag_type: FlagType
    status: FlagStatus
    customer_id: uuid.UUID | None
    staff_user_id: uuid.UUID | None
    related_type: str | None
    related_id: uuid.UUID | None
    summary: str
    detail: dict[str, object] | None
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    resolution_note: str | None
    task_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
