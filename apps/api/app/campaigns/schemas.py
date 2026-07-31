from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CampaignStatus = Literal[
    "draft",
    "ready",
    "scheduled",
    "running",
    "paused",
    "completed",
    "cancelled",
    "failed",
    "archived",
]
CampaignRecipientStatus = Literal["pending", "eligible", "suppressed", "sent", "failed"]


class CampaignCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    objective: str | None = Field(default=None, max_length=60)
    campaign_type: str | None = Field(default=None, max_length=40)
    channel_templates: dict[str, str] = Field(min_length=1)
    target_segment_ids: list[uuid.UUID] = Field(min_length=1)
    excluded_segment_ids: list[uuid.UUID] | None = None
    linked_offer_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None
    send_window_start_local: str | None = Field(default=None, max_length=5)
    send_window_end_local: str | None = Field(default=None, max_length=5)
    budget_minor: int | None = Field(default=None, ge=0)
    owner_staff_id: uuid.UUID | None = None


class CampaignUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    objective: str | None = Field(default=None, max_length=60)
    campaign_type: str | None = Field(default=None, max_length=40)
    channel_templates: dict[str, str] | None = None
    target_segment_ids: list[uuid.UUID] | None = None
    excluded_segment_ids: list[uuid.UUID] | None = None
    linked_offer_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None
    send_window_start_local: str | None = Field(default=None, max_length=5)
    send_window_end_local: str | None = Field(default=None, max_length=5)
    budget_minor: int | None = Field(default=None, ge=0)
    owner_staff_id: uuid.UUID | None = None


class CampaignTransitionIn(BaseModel):
    target_status: CampaignStatus
    reason: str | None = None


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    objective: str | None
    campaign_type: str | None
    status: CampaignStatus
    channel_templates: dict[str, object]
    target_segment_ids: list[str]
    excluded_segment_ids: list[str] | None
    linked_offer_id: uuid.UUID | None
    scheduled_at: datetime | None
    send_window_start_local: str | None
    send_window_end_local: str | None
    audience_snapshot_taken_at: datetime | None
    estimated_size: int | None
    budget_minor: int | None
    owner_staff_id: uuid.UUID | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_reason: str | None
    created_at: datetime
    updated_at: datetime


class CampaignRecipientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_id: uuid.UUID
    customer_id: uuid.UUID
    channel_id: uuid.UUID
    source_segment_id: uuid.UUID | None
    status: CampaignRecipientStatus
    eligibility_reason: str | None
    suppression_reason: str | None
    scheduled_message_id: uuid.UUID | None
    message_id: uuid.UUID | None
    attempt_count: int
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    opened_at: datetime | None
    clicked_at: datetime | None
    failure_reason: str | None
    created_at: datetime


class BuildAudienceOut(BaseModel):
    campaign_id: uuid.UUID
    estimated_size: int
    audience_snapshot_taken_at: datetime


class LaunchCampaignOut(BaseModel):
    campaign_id: uuid.UUID
    queued_count: int
    suppressed_count: int


class CampaignAnalyticsOut(BaseModel):
    campaign_id: uuid.UUID
    total_recipients: int
    pending: int
    eligible: int
    suppressed: int
    sent: int
    failed: int
