from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RecoveryType = Literal[
    "apology_only",
    "replacement",
    "refund_request",
    "approved_refund",
    "discount",
    "coupon",
    "loyalty_credit",
    "complimentary_item",
    "manager_follow_up",
    "operational_correction",
]
RecoveryStatus = Literal[
    "proposed",
    "approval_required",
    "approved",
    "rejected",
    "executing",
    "completed",
    "failed",
    "reversed",
    "cancelled",
]

# Types that are money-denominated (`value_minor`) vs. points-denominated
# (`points`) vs. carry no quantity at all — GROWTH_AND_INTELLIGENCE.md
# section 12.6.
_MONEY_TYPES = {"refund_request", "approved_refund", "discount", "complimentary_item"}
_POINTS_TYPES = {"loyalty_credit"}


class RecoveryActionProposeIn(BaseModel):
    recovery_type: RecoveryType
    value_minor: int | None = Field(default=None, ge=0)
    points: int | None = Field(default=None, ge=0)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def _requires_correct_quantity(self) -> RecoveryActionProposeIn:
        if self.recovery_type in _MONEY_TYPES and self.value_minor is None:
            raise ValueError(f"recovery_type={self.recovery_type!r} requires value_minor.")
        if self.recovery_type in _POINTS_TYPES and self.points is None:
            raise ValueError(f"recovery_type={self.recovery_type!r} requires points.")
        return self


class RecoveryActionRejectIn(BaseModel):
    reason: str = Field(min_length=1)


class RecoveryActionReverseIn(BaseModel):
    reason: str = Field(min_length=1)


class RecoveryActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_id: uuid.UUID
    customer_id: uuid.UUID
    recovery_type: RecoveryType
    status: RecoveryStatus
    value_minor: int | None
    points: int | None
    description: str
    proposed_by_staff_id: uuid.UUID
    proposed_at: datetime
    approval_required: bool
    approval_rule_id: uuid.UUID | None
    approved_by_staff_id: uuid.UUID | None
    approved_at: datetime | None
    rejected_reason: str | None
    executed_at: datetime | None
    execution_reference_type: str | None
    execution_reference_id: uuid.UUID | None
    failed_reason: str | None
    reversed_at: datetime | None
    reversed_by_staff_id: uuid.UUID | None
    reversal_reason: str | None
    created_at: datetime
    updated_at: datetime


class ActionHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: RecoveryStatus | None
    to_status: RecoveryStatus
    actor_id: uuid.UUID | None
    reason: str | None
    created_at: datetime


class ApprovalRuleCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    recovery_type: RecoveryType | None = None
    min_value_minor: int | None = Field(default=None, ge=0)
    max_value_minor: int | None = Field(default=None, ge=0)
    applicable_severities: list[str] | None = None
    required_permission: str = Field(min_length=1, max_length=100)
    allow_self_approval: bool = False


class ApprovalRuleUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None
    recovery_type: RecoveryType | None = None
    min_value_minor: int | None = Field(default=None, ge=0)
    max_value_minor: int | None = Field(default=None, ge=0)
    applicable_severities: list[str] | None = None
    required_permission: str | None = Field(default=None, min_length=1, max_length=100)
    allow_self_approval: bool | None = None


class ApprovalRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    is_active: bool
    recovery_type: RecoveryType | None
    min_value_minor: int | None
    max_value_minor: int | None
    applicable_severities: list[str] | None
    required_permission: str
    allow_self_approval: bool
    created_at: datetime
    updated_at: datetime


class RecoveryAnalyticsOut(BaseModel):
    by_type: list[dict[str, int | str]]
    by_status: list[dict[str, int | str]]
    total_value_minor_30d: int
    total_points_30d: int
    approved_count_30d: int
    rejected_count_30d: int
    completion_rate_pct: float
