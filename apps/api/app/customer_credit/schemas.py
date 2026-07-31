from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AccountStatus = Literal["active", "suspended", "closed"]
EntryType = Literal["issue", "redeem", "reverse", "adjust", "expire", "migration"]
IssueReason = Literal[
    "service_recovery",
    "refund_as_credit",
    "campaign_reward",
    "referral_reward",
    "achievement_reward",
    "goodwill_adjustment",
    "migration",
]


class EnsureAccountIn(BaseModel):
    customer_id: uuid.UUID


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    status: AccountStatus
    current_balance_minor: int
    created_at: datetime
    updated_at: datetime


class IssueIn(BaseModel):
    account_id: uuid.UUID
    amount_minor: int = Field(gt=0)
    issue_reason: IssueReason
    idempotency_key: str = Field(min_length=1, max_length=160)
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    reason: str | None = None
    approval_reference: str | None = None


class RedeemIn(BaseModel):
    account_id: uuid.UUID
    amount_minor: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=160)
    source_type: str | None = None
    source_id: uuid.UUID | None = None
    reason: str | None = None


class AdjustIn(BaseModel):
    account_id: uuid.UUID
    amount_delta_minor: int
    reason: str
    idempotency_key: str = Field(min_length=1, max_length=160)
    approval_reference: str | None = None


class ReverseIn(BaseModel):
    entry_id: uuid.UUID
    reason: str
    idempotency_key: str = Field(min_length=1, max_length=160)


class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    entry_type: EntryType
    issue_reason: IssueReason | None
    amount_delta_minor: int
    balance_after_minor: int
    source_type: str | None
    source_id: uuid.UUID | None
    idempotency_key: str
    reason: str | None
    approval_reference: str | None
    reversal_of_id: uuid.UUID | None
    created_by: uuid.UUID | None
    effective_at: datetime
    created_at: datetime


class CreditAnalyticsOut(BaseModel):
    active_accounts: int
    outstanding_liability_minor: int
    issued_30d_minor: int
    redeemed_30d_minor: int
