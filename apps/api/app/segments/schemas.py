from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from app.commercial_rules.schema import RuleNode
from pydantic import BaseModel, ConfigDict, Field, model_validator

SegmentType = Literal["dynamic", "static"]
SegmentStatus = Literal["draft", "active", "archived"]


class SegmentCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    segment_type: SegmentType
    rule_definition: RuleNode | None = None
    refresh_strategy: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def _rule_required_for_dynamic(self) -> SegmentCreateIn:
        if self.segment_type == "dynamic" and self.rule_definition is None:
            raise ValueError("A dynamic segment requires a rule_definition.")
        if self.segment_type == "static" and self.rule_definition is not None:
            raise ValueError("A static segment must not have a rule_definition.")
        return self


class SegmentUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    rule_definition: RuleNode | None = None
    refresh_strategy: str | None = Field(default=None, max_length=30)


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    segment_type: SegmentType
    status: SegmentStatus
    rule_definition: dict[str, object] | None
    rule_version: int
    refresh_strategy: str | None
    estimated_count: int | None
    last_computed_count: int | None
    last_refreshed_at: datetime | None
    owner_staff_id: uuid.UUID | None
    is_seed_builtin: bool
    created_at: datetime
    updated_at: datetime


class SegmentTransitionIn(BaseModel):
    target_status: SegmentStatus


class MembershipAddIn(BaseModel):
    customer_id: uuid.UUID
    reason: str | None = None


class MembershipRemoveIn(BaseModel):
    customer_id: uuid.UUID
    reason: str | None = None


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    segment_id: uuid.UUID
    customer_id: uuid.UUID
    action: Literal["added", "removed"]
    source: str | None
    added_by: uuid.UUID | None
    reason: str | None
    created_at: datetime


class SegmentPreviewOut(BaseModel):
    eligible: bool
    matched_facts: list[str]
    failed_facts: list[str]
    unknown_facts: list[str]


class SegmentRefreshOut(BaseModel):
    segment_id: uuid.UUID
    computed_count: int
    refreshed_at: datetime
