from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GiftCardStatus = Literal[
    "draft",
    "active",
    "partially_redeemed",
    "fully_redeemed",
    "expired",
    "suspended",
    "cancelled",
]
LedgerEntryType = Literal[
    "issue", "activate", "redeem", "reverse", "adjust", "expire", "cancel", "migration"
]


class IssueGiftCardIn(BaseModel):
    initial_amount_minor: int = Field(gt=0)
    purchaser_customer_id: uuid.UUID | None = None
    purchaser_contact: str | None = Field(default=None, max_length=200)
    recipient_customer_id: uuid.UUID | None = None
    recipient_name: str | None = Field(default=None, max_length=160)
    recipient_contact: str | None = Field(default=None, max_length=200)
    expires_at: datetime | None = None
    pin: str | None = Field(default=None, min_length=4, max_length=12)
    source_order_id: uuid.UUID | None = None
    notes: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)


class GiftCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    card_number: str
    masked_display: str
    purchaser_customer_id: uuid.UUID | None
    purchaser_contact: str | None
    recipient_customer_id: uuid.UUID | None
    recipient_name: str | None
    recipient_contact: str | None
    initial_amount_minor: int
    current_balance_minor: int
    status: GiftCardStatus
    issued_at: datetime | None
    purchased_at: datetime | None
    activated_at: datetime | None
    expires_at: datetime | None
    source_order_id: uuid.UUID | None
    delivery_status: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class IssueGiftCardOut(BaseModel):
    gift_card: GiftCardOut
    code: str


class RevealCodeOut(BaseModel):
    card_number: str
    code_last4: str


class StatusActionIn(BaseModel):
    reason: str | None = None


class RedeemGiftCardIn(BaseModel):
    code: str = Field(min_length=1)
    pin: str | None = None
    amount_minor: int = Field(gt=0)
    order_id: uuid.UUID | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)


class AdjustGiftCardIn(BaseModel):
    amount_delta_minor: int
    reason: str
    idempotency_key: str = Field(min_length=1, max_length=160)


class ReverseEntryIn(BaseModel):
    entry_id: uuid.UUID
    reason: str
    idempotency_key: str = Field(min_length=1, max_length=160)


class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gift_card_id: uuid.UUID
    entry_type: LedgerEntryType
    amount_delta_minor: int
    balance_after_minor: int
    source_type: str | None
    source_id: uuid.UUID | None
    idempotency_key: str
    reason: str | None
    reversal_of_id: uuid.UUID | None
    created_by: uuid.UUID | None
    effective_at: datetime
    created_at: datetime


class GiftCardAnalyticsOut(BaseModel):
    active_cards: int
    outstanding_liability_minor: int
    issued_30d_minor: int
    redeemed_30d_minor: int
