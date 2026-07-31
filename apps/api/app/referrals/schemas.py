from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReferralProgramStatus = Literal["draft", "active", "paused", "archived"]
ReferralRelationshipStatus = Literal[
    "invited", "attributed", "qualified", "rewarded", "rejected", "cancelled"
]


class ProgramCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    referrer_eligibility_note: str | None = None
    referee_eligibility_note: str | None = None
    qualifying_order_minimum_minor: int | None = Field(default=None, ge=0)
    reward_ledger: Literal["loyalty_points", "internal_credit"] = "loyalty_points"
    referrer_reward_amount: int = Field(gt=0)
    referee_reward_amount: int = Field(gt=0)
    max_active_codes_per_referrer: int = Field(default=1, gt=0)
    max_rewarded_referrals_per_window: int | None = Field(default=None, gt=0)
    window_days: int | None = Field(default=None, gt=0)
    reward_hold_days: int = Field(default=0, ge=0)


class ProgramUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    referrer_eligibility_note: str | None = None
    referee_eligibility_note: str | None = None
    qualifying_order_minimum_minor: int | None = Field(default=None, ge=0)
    referrer_reward_amount: int | None = Field(default=None, gt=0)
    referee_reward_amount: int | None = Field(default=None, gt=0)
    max_active_codes_per_referrer: int | None = Field(default=None, gt=0)
    max_rewarded_referrals_per_window: int | None = Field(default=None, gt=0)
    window_days: int | None = Field(default=None, gt=0)
    reward_hold_days: int | None = Field(default=None, ge=0)


class ProgramTransitionIn(BaseModel):
    target_status: ReferralProgramStatus


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    status: ReferralProgramStatus
    starts_at: datetime | None
    ends_at: datetime | None
    referrer_eligibility_note: str | None
    referee_eligibility_note: str | None
    qualifying_order_minimum_minor: int | None
    reward_ledger: Literal["loyalty_points", "internal_credit"]
    referrer_reward_amount: int
    referee_reward_amount: int
    max_active_codes_per_referrer: int
    max_rewarded_referrals_per_window: int | None
    window_days: int | None
    reward_hold_days: int
    version: int
    is_active_default: bool
    created_at: datetime
    updated_at: datetime


class IssueCodeIn(BaseModel):
    referrer_customer_id: uuid.UUID
    expires_at: datetime | None = None


class CodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    program_id: uuid.UUID
    referrer_customer_id: uuid.UUID
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class AttributeReferralIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    referred_contact: str = Field(min_length=1)
    referred_customer_id: uuid.UUID | None = None


class QualifyReferralIn(BaseModel):
    qualifying_order_id: uuid.UUID


class RejectReferralIn(BaseModel):
    reason: str


class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    program_id: uuid.UUID
    code_id: uuid.UUID
    referrer_customer_id: uuid.UUID
    referred_identity_key: str
    referred_customer_id: uuid.UUID | None
    attributed_at: datetime
    qualifying_order_id: uuid.UUID | None
    status: ReferralRelationshipStatus
    referrer_reward_ledger_entry_id: uuid.UUID | None
    referee_reward_ledger_entry_id: uuid.UUID | None
    rejection_reason: str | None
    qualified_at: datetime | None
    rewarded_at: datetime | None
    created_at: datetime
