import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

ProgramStatus = Literal["draft", "active", "paused", "archived"]
TierQualificationMetric = Literal[
    "lifetime_spend", "rolling_spend", "points_earned", "completed_orders", "visits", "manual"
]
LoyaltyAccountStatus = Literal["active", "suspended", "closed", "merged"]
LedgerEntryType = Literal[
    "earn_order",
    "earn_campaign",
    "earn_manual",
    "redeem_order",
    "redeem_reward",
    "expire",
    "reverse_earn",
    "reverse_redemption",
    "service_recovery_credit",
    "merge_transfer",
    "correction",
    "referral_reward",
    "achievement_reward",
]


class ProgramCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    points_display_name: str = Field(default="points", max_length=60)
    description: str | None = None
    points_per_currency_unit: int = Field(default=1, gt=0)
    currency_unit_minor: int = Field(default=1000, gt=0)
    redemption_points_per_unit: int = Field(default=100, gt=0)
    redemption_value_minor: int = Field(default=2500, gt=0)
    minimum_redemption_points: int = Field(default=300, ge=0)
    max_redemption_percent: Decimal | None = Field(default=None, gt=0, le=100)
    points_expiry_days: int | None = Field(default=365, gt=0)
    terms_summary: str | None = None
    is_default: bool = False


class ProgramUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    points_expiry_days: int | None = Field(default=None, gt=0)
    max_redemption_percent: Decimal | None = Field(default=None, gt=0, le=100)
    terms_summary: str | None = None


class ProgramTransitionIn(BaseModel):
    target_status: ProgramStatus


class ProgramOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    points_display_name: str
    description: str | None
    status: ProgramStatus
    is_default: bool
    points_per_currency_unit: int
    currency_unit_minor: int
    redemption_points_per_unit: int
    redemption_value_minor: int
    minimum_redemption_points: int
    max_redemption_percent: Decimal | None
    points_expiry_days: int | None
    terms_summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TierCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=120)
    rank: int = Field(ge=0)
    qualification_metric: TierQualificationMetric
    threshold: Decimal = Field(ge=0)
    rolling_window_days: int | None = Field(default=None, gt=0)
    benefits_summary: str | None = None
    points_multiplier: Decimal = Field(default=Decimal("1.00"), gt=0)
    review_period_days: int | None = Field(default=None, gt=0)
    downgrade_grace_days: int | None = Field(default=None, gt=0)
    icon: str | None = None
    color: str | None = None


class TierOut(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    code: str
    name: str
    rank: int
    qualification_metric: TierQualificationMetric
    threshold: Decimal
    rolling_window_days: int | None
    benefits_summary: str | None
    points_multiplier: Decimal
    is_active: bool
    icon: str | None
    color: str | None

    model_config = {"from_attributes": True}


class AccountOut(BaseModel):
    id: uuid.UUID
    account_number: str
    customer_id: uuid.UUID
    program_id: uuid.UUID
    status: LoyaltyAccountStatus
    points_balance: int
    lifetime_points_earned: int
    lifetime_points_redeemed: int
    lifetime_points_expired: int
    current_tier_id: uuid.UUID | None
    enrolled_at: datetime

    model_config = {"from_attributes": True}


class LedgerEntryOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    entry_type: LedgerEntryType
    points_delta: int
    balance_after: int
    source_type: str | None
    source_id: uuid.UUID | None
    description: str | None
    effective_at: datetime
    expiry_at: datetime | None
    reversal_of_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnrollIn(BaseModel):
    customer_id: uuid.UUID
    program_id: uuid.UUID | None = None
    enrollment_source: str | None = None


class EarnIn(BaseModel):
    account_id: uuid.UUID
    entry_type: Literal["earn_order", "earn_campaign", "earn_manual", "service_recovery_credit"]
    points: int = Field(gt=0)
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    description: str | None = None
    idempotency_key: str
    expiry_at: datetime | None = None


class RedeemIn(BaseModel):
    account_id: uuid.UUID
    entry_type: Literal["redeem_order", "redeem_reward"] = "redeem_order"
    points: int = Field(gt=0)
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    description: str | None = None
    idempotency_key: str


class AdjustIn(BaseModel):
    account_id: uuid.UUID
    points_delta: int
    reason: str = Field(min_length=1)
    idempotency_key: str
    approval_reference: str | None = None


class ReverseIn(BaseModel):
    entry_id: uuid.UUID
    reason: str = Field(min_length=1)
    idempotency_key: str


class TierAssignIn(BaseModel):
    tier_id: uuid.UUID
    reason: str = Field(min_length=1)


class LoyaltyAnalyticsOut(BaseModel):
    active_members: int
    points_issued_30d: int
    points_redeemed_30d: int
    points_expired_30d: int
    outstanding_points_liability_minor: int
    redemption_rate_pct: Decimal
    tier_distribution: list[dict[str, int | str | None]]
