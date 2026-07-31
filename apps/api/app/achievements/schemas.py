from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from app.commercial_rules.schema import RuleNode
from pydantic import BaseModel, ConfigDict, Field

RewardLedger = Literal["none", "loyalty_points", "internal_credit"]


class AchievementCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=60)
    condition: RuleNode
    is_active: bool = True
    is_hidden: bool = False
    reward_ledger: RewardLedger = "none"
    reward_amount: int | None = Field(default=None, gt=0)
    is_repeatable: bool = False
    cooldown_days: int | None = Field(default=None, gt=0)


class AchievementUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = Field(default=None, max_length=60)
    condition: RuleNode | None = None
    is_active: bool | None = None
    is_hidden: bool | None = None
    reward_ledger: RewardLedger | None = None
    reward_amount: int | None = Field(default=None, gt=0)
    is_repeatable: bool | None = None
    cooldown_days: int | None = Field(default=None, gt=0)


class AchievementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    icon: str | None
    condition_version: int
    condition: dict[str, object]
    is_active: bool
    is_hidden: bool
    reward_ledger: RewardLedger
    reward_amount: int | None
    is_repeatable: bool
    cooldown_days: int | None
    created_at: datetime
    updated_at: datetime


class EvaluateAwardIn(BaseModel):
    achievement_id: uuid.UUID
    customer_id: uuid.UUID
    source_event_type: str = Field(min_length=1, max_length=60)
    source_event_key: str = Field(min_length=1, max_length=160)


class ReverseAwardIn(BaseModel):
    reason: str


class AwardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    achievement_id: uuid.UUID
    customer_id: uuid.UUID
    source_event_type: str
    source_event_key: str
    is_repeatable_award: bool
    reward_ledger_entry_id: uuid.UUID | None
    reversed_at: datetime | None
    reversal_reason: str | None
    awarded_at: datetime
