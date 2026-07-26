import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.customers.schemas import CustomerListItemOut
from app.shared.normalization import NormalizationError, normalize_email, normalize_phone

LeadType = Literal[
    "corporate_catering",
    "recurring_office_order",
    "event_booking",
    "group_dining",
    "partnership",
    "franchise_or_business_enquiry",
    "general_sales_enquiry",
]
LeadSource = Literal[
    "website",
    "phone",
    "walk_in",
    "whatsapp",
    "zomato_import",
    "swiggy_import",
    "meta_campaign",
    "google_campaign",
    "referral",
    "corporate_outreach",
    "event_enquiry",
    "offline_qr",
]
LeadStatus = Literal[
    "new",
    "contacted",
    "qualified",
    "interested",
    "follow_up_scheduled",
    "proposal_shared",
    "negotiating",
    "won",
    "lost",
    "closed",
]
LeadPriority = Literal["low", "normal", "high", "urgent"]
LostReason = Literal[
    "budget",
    "timing",
    "no_response",
    "chose_competitor",
    "service_unavailable",
    "location_issue",
    "menu_mismatch",
    "duplicate",
    "invalid_enquiry",
]
LeadActivityType = Literal[
    "call",
    "email",
    "whatsapp",
    "meeting",
    "proposal",
    "note",
    "status_change",
    "assignment",
    "follow_up_created",
    "follow_up_completed",
    "file_added",
    "customer_conversion",
    "order_conversion",
]
FollowUpStatus = Literal["scheduled", "due", "completed", "cancelled", "missed"]


def _validated_phone(value: str | None) -> str | None:
    try:
        return normalize_phone(value)
    except NormalizationError as exc:
        raise ValueError(str(exc)) from exc


def _validated_email(value: str | None) -> str | None:
    try:
        return normalize_email(value)
    except NormalizationError as exc:
        raise ValueError(str(exc)) from exc


class LeadCreateIn(BaseModel):
    lead_type: LeadType
    display_name: str = Field(min_length=1, max_length=200)
    organization_name: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=160)
    phone_e164: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    source: LeadSource
    campaign_reference: str | None = Field(default=None, max_length=200)
    priority: LeadPriority = "normal"
    estimated_value_minor: int | None = Field(default=None, ge=0)
    party_size: int | None = Field(default=None, ge=1)
    requested_date: date | None = None
    requested_time: time | None = None
    assigned_staff_id: uuid.UUID | None = None
    description: str | None = None
    qualification_notes: str | None = None
    food_preferences: str | None = None
    budget_notes: str | None = None

    @field_validator("phone_e164")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class LeadUpdateIn(BaseModel):
    lead_type: LeadType | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    organization_name: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=160)
    phone_e164: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    campaign_reference: str | None = Field(default=None, max_length=200)
    priority: LeadPriority | None = None
    estimated_value_minor: int | None = Field(default=None, ge=0)
    party_size: int | None = Field(default=None, ge=1)
    requested_date: date | None = None
    requested_time: time | None = None
    description: str | None = None
    qualification_notes: str | None = None
    food_preferences: str | None = None
    budget_notes: str | None = None
    do_not_contact: bool | None = None
    expected_version: int | None = None

    @field_validator("phone_e164")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class LeadAssignIn(BaseModel):
    assigned_staff_id: uuid.UUID


class LeadTransitionIn(BaseModel):
    new_status: LeadStatus
    reason: str | None = Field(default=None, max_length=500)
    lost_reason: LostReason | None = None


class LeadArchiveIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class LeadListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_number: str
    display_name: str
    organization_name: str | None
    lead_type: str
    source: str
    status: str
    priority: str
    estimated_value_minor: int | None
    requested_date: date | None
    party_size: int | None
    assigned_staff_id: uuid.UUID | None
    next_follow_up_at: datetime | None
    last_contact_at: datetime | None
    created_at: datetime


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_number: str
    lead_type: str
    display_name: str
    organization_name: str | None
    contact_name: str | None
    phone_e164: str | None
    email: str | None
    source: str
    campaign_reference: str | None
    status: str
    priority: str
    estimated_value_minor: int | None
    party_size: int | None
    requested_date: date | None
    requested_time: time | None
    assigned_staff_id: uuid.UUID | None
    next_follow_up_at: datetime | None
    last_contact_at: datetime | None
    won_customer_id: uuid.UUID | None
    lost_reason: str | None
    description: str | None
    qualification_notes: str | None
    food_preferences: str | None
    budget_notes: str | None
    do_not_contact: bool
    converted_at: datetime | None
    converted_by: uuid.UUID | None
    version: int
    created_at: datetime
    updated_at: datetime


class LeadActivityIn(BaseModel):
    activity_type: LeadActivityType
    summary: str = Field(min_length=1)
    occurred_at: datetime | None = None


class LeadActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    activity_type: str
    summary: str
    performed_by: uuid.UUID | None
    occurred_at: datetime


class LeadFollowUpCreateIn(BaseModel):
    scheduled_at: datetime
    assigned_to: uuid.UUID
    purpose: str | None = None
    channel: str | None = Field(default=None, max_length=32)


class LeadFollowUpCompleteIn(BaseModel):
    outcome: str | None = None


class LeadFollowUpRescheduleIn(BaseModel):
    scheduled_at: datetime
    reason: str | None = None


class LeadFollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    assigned_to: uuid.UUID
    scheduled_at: datetime
    status: str
    completed_at: datetime | None
    outcome: str | None
    purpose: str | None
    channel: str | None
    completed_by: uuid.UUID | None


class DuplicateLeadMatchOut(BaseModel):
    lead: LeadListItemOut
    match_reasons: list[str]


class ConversionPreviewIn(BaseModel):
    lead_id: uuid.UUID
    existing_customer_id: uuid.UUID | None = None


class ConversionPreviewOut(BaseModel):
    lead: LeadOut
    possible_customer_matches: list[CustomerListItemOut] = Field(default_factory=list)
    will_create_new_customer: bool


class ConversionExecuteIn(BaseModel):
    existing_customer_id: uuid.UUID | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)
