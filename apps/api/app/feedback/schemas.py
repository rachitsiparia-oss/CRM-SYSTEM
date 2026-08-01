from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FeedbackSource = Literal[
    "post_order",
    "post_reservation",
    "website",
    "whatsapp",
    "email",
    "manual_entry",
    "public_review_reference",
    "campaign",
]
FeedbackStatus = Literal[
    "new", "acknowledged", "under_review", "action_required", "resolved", "closed", "spam"
]
FeedbackPriority = Literal["low", "normal", "high", "urgent"]
SentimentLabel = Literal["positive", "neutral", "negative", "mixed"]
RatingDimension = Literal[
    "overall",
    "food_quality",
    "taste",
    "packaging",
    "delivery",
    "speed",
    "staff_service",
    "cleanliness",
    "reservation_experience",
    "value",
]


class RatingIn(BaseModel):
    dimension: RatingDimension
    rating: int = Field(ge=1, le=5)


class FeedbackCreateIn(BaseModel):
    customer_id: uuid.UUID | None = None
    guest_name: str | None = Field(default=None, max_length=160)
    guest_contact: str | None = Field(default=None, max_length=200)
    source: FeedbackSource
    order_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    campaign_id: uuid.UUID | None = None
    comment: str | None = None
    sentiment: SentimentLabel | None = None
    consent_for_follow_up: bool = False
    ratings: list[RatingIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _requires_identity(self) -> FeedbackCreateIn:
        if self.customer_id is None and self.guest_name is None and self.guest_contact is None:
            raise ValueError("Feedback requires either a customer_id or a guest name/contact.")
        return self


class FeedbackUpdateIn(BaseModel):
    assigned_staff_id: uuid.UUID | None = None
    priority: FeedbackPriority | None = None
    sentiment: SentimentLabel | None = None
    comment: str | None = None


class FeedbackTransitionIn(BaseModel):
    target_status: FeedbackStatus
    reason: str | None = None


class ConvertToComplaintIn(BaseModel):
    category: str
    severity: str
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dimension: RatingDimension
    rating: int


class FeedbackStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: FeedbackStatus | None
    to_status: FeedbackStatus
    actor_id: uuid.UUID | None
    reason: str | None
    created_at: datetime


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    feedback_number: str
    customer_id: uuid.UUID | None
    guest_name: str | None
    guest_contact: str | None
    source: FeedbackSource
    order_id: uuid.UUID | None
    reservation_id: uuid.UUID | None
    campaign_id: uuid.UUID | None
    comment: str | None
    sentiment: SentimentLabel | None
    consent_for_follow_up: bool
    assigned_staff_id: uuid.UUID | None
    status: FeedbackStatus
    priority: FeedbackPriority
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    converted_to_complaint_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class TagAssignIn(BaseModel):
    tag_ids: list[uuid.UUID] = Field(default_factory=list)


class FeedbackAnalyticsOut(BaseModel):
    total_30d: int
    average_overall_rating: float | None
    positive_count_30d: int
    neutral_count_30d: int
    negative_count_30d: int
    converted_to_complaint_30d: int
    by_source: list[dict[str, int | str]]


# --- Review requests -----------------------------------------------------

ReviewRequestSourceType = Literal["order", "reservation"]
ReviewRequestChannel = Literal["whatsapp", "email", "sms"]
ReviewRequestStatus = Literal[
    "draft",
    "eligible",
    "scheduled",
    "sent",
    "delivered",
    "opened",
    "completed",
    "expired",
    "suppressed",
    "cancelled",
    "failed",
]


class ReviewRequestCreateIn(BaseModel):
    customer_id: uuid.UUID
    source_type: ReviewRequestSourceType
    order_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    channel: ReviewRequestChannel

    @model_validator(mode="after")
    def _requires_matching_source(self) -> ReviewRequestCreateIn:
        if self.source_type == "order" and self.order_id is None:
            raise ValueError("source_type='order' requires order_id.")
        if self.source_type == "reservation" and self.reservation_id is None:
            raise ValueError("source_type='reservation' requires reservation_id.")
        return self


class ReviewRequestCompleteIn(BaseModel):
    comment: str | None = None
    sentiment: SentimentLabel | None = None
    ratings: list[RatingIn] = Field(default_factory=list)


class ReviewRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    source_type: ReviewRequestSourceType
    order_id: uuid.UUID | None
    reservation_id: uuid.UUID | None
    channel: ReviewRequestChannel
    status: ReviewRequestStatus
    eligibility_reason: str | None
    suppression_reason: str | None
    scheduled_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    opened_at: datetime | None
    completed_at: datetime | None
    expired_at: datetime | None
    failure_reason: str | None
    resulting_feedback_id: uuid.UUID | None
    created_at: datetime


class ReviewRequestAnalyticsOut(BaseModel):
    total_30d: int
    sent_30d: int
    completed_30d: int
    completion_rate_pct: float
    suppressed_30d: int
