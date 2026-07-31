from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from app.commercial_rules.schema import RuleNode
from app.offers.benefit import BenefitRule
from pydantic import BaseModel, ConfigDict, Field

OfferType = Literal[
    "percentage_discount",
    "fixed_discount",
    "item_discount",
    "category_discount",
    "buy_x_get_y",
    "combo_price",
    "free_item",
    "delivery_fee_discount",
    "loyalty_bonus",
    "internal_credit",
    "service_recovery",
]
OfferStatus = Literal[
    "draft", "in_review", "approved", "active", "paused", "expired", "cancelled", "archived"
]


class OfferVersionCreateIn(BaseModel):
    eligibility_rule: RuleNode
    benefit_rule: BenefitRule
    minimum_order_value_minor: int | None = Field(default=None, ge=0)
    maximum_discount_minor: int | None = Field(default=None, ge=0)
    applicable_product_ids: list[str] | None = None
    excluded_product_ids: list[str] | None = None
    applicable_category_ids: list[str] | None = None
    channel_eligibility: list[str] | None = None
    day_time_windows: dict[str, Any] | None = None
    global_usage_limit: int | None = Field(default=None, gt=0)
    per_customer_usage_limit: int | None = Field(default=None, gt=0)
    valid_from: datetime
    valid_until: datetime | None = None


class OfferCreateIn(BaseModel):
    offer_code: str = Field(min_length=1, max_length=60)
    internal_name: str = Field(min_length=1, max_length=160)
    customer_facing_name: str = Field(min_length=1, max_length=160)
    offer_type: OfferType
    requires_code: bool = False
    stackability_group: str | None = Field(default=None, max_length=60)
    is_exclusive: bool = False
    budget_cap_minor: int | None = Field(default=None, ge=0)
    redemption_cap: int | None = Field(default=None, gt=0)
    requires_approval: bool = False
    financial_owner_id: uuid.UUID | None = None
    terms_and_notes: str | None = None
    initial_version: OfferVersionCreateIn


class OfferUpdateIn(BaseModel):
    internal_name: str | None = Field(default=None, min_length=1, max_length=160)
    customer_facing_name: str | None = Field(default=None, min_length=1, max_length=160)
    stackability_group: str | None = Field(default=None, max_length=60)
    is_exclusive: bool | None = None
    budget_cap_minor: int | None = Field(default=None, ge=0)
    redemption_cap: int | None = Field(default=None, gt=0)
    financial_owner_id: uuid.UUID | None = None
    terms_and_notes: str | None = None


class OfferTransitionIn(BaseModel):
    target_status: OfferStatus


class OfferVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    version_number: int
    eligibility_rule: dict[str, object]
    benefit_rule: dict[str, object]
    minimum_order_value_minor: int | None
    maximum_discount_minor: int | None
    applicable_product_ids: list[str] | None
    excluded_product_ids: list[str] | None
    applicable_category_ids: list[str] | None
    channel_eligibility: list[str] | None
    day_time_windows: dict[str, object] | None
    global_usage_limit: int | None
    per_customer_usage_limit: int | None
    valid_from: datetime
    valid_until: datetime | None
    created_by: uuid.UUID | None
    created_at: datetime


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_code: str
    internal_name: str
    customer_facing_name: str
    offer_type: OfferType
    status: OfferStatus
    requires_code: bool
    stackability_group: str | None
    is_exclusive: bool
    budget_cap_minor: int | None
    redemption_cap: int | None
    redemption_count: int
    requires_approval: bool
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    financial_owner_id: uuid.UUID | None
    terms_and_notes: str | None
    latest_version_number: int
    latest_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CouponCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    is_reusable: bool = False
    customer_id: uuid.UUID | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    redemption_limit: int | None = Field(default=None, gt=0)
    generation_batch: str | None = Field(default=None, max_length=60)


class CouponOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    offer_id: uuid.UUID
    is_reusable: bool
    customer_id: uuid.UUID | None
    starts_at: datetime | None
    expires_at: datetime | None
    redemption_limit: int | None
    redemption_count: int
    source_campaign_id: uuid.UUID | None
    generation_batch: str | None
    is_active: bool
    created_at: datetime


class OfferPreviewIn(BaseModel):
    customer_id: uuid.UUID
    coupon_code: str | None = None
    order_channel: str | None = None
    order_type: str | None = None
    subtotal_minor: int = Field(ge=0)
    product_ids: list[str] = Field(default_factory=list)
    category_ids: list[str] = Field(default_factory=list)
    eligible_amount_minor: int = Field(ge=0)


class OfferPreviewOut(BaseModel):
    eligible: bool
    matched_facts: list[str]
    failed_facts: list[str]
    unknown_facts: list[str]
    discount_amount_minor: int
    reasons: list[str]


class ReserveRedemptionIn(BaseModel):
    offer_id: uuid.UUID
    customer_id: uuid.UUID
    coupon_code: str | None = None
    order_id: uuid.UUID | None = None
    order_channel: str | None = None
    order_type: str | None = None
    subtotal_minor: int = Field(ge=0)
    product_ids: list[str] = Field(default_factory=list)
    category_ids: list[str] = Field(default_factory=list)
    eligible_amount_minor: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=160)


class ConfirmRedemptionIn(BaseModel):
    order_id: uuid.UUID


class RejectRedemptionIn(BaseModel):
    reason: str


class ReverseRedemptionIn(BaseModel):
    reason: str


class OfferRedemptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    offer_version_id: uuid.UUID
    coupon_id: uuid.UUID | None
    customer_id: uuid.UUID
    order_id: uuid.UUID | None
    entered_code: str | None
    eligible_amount_minor: int
    discount_amount_minor: int
    status: Literal["reserved", "applied", "confirmed", "reversed", "rejected", "expired"]
    evaluation_explanation: dict[str, object]
    idempotency_key: str
    reservation_expires_at: datetime | None
    confirmed_at: datetime | None
    reversed_at: datetime | None
    reversal_reason: str | None
    created_at: datetime
