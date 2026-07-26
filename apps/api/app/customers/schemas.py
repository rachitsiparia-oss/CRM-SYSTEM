import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.normalization import NormalizationError, normalize_email, normalize_phone

CustomerType = Literal["individual", "corporate"]
CustomerStatus = Literal["active", "inactive", "blacklisted", "archived", "merged"]
CustomerSegment = Literal[
    "new",
    "repeat",
    "loyal",
    "vip",
    "at_risk",
    "dormant",
    "high_aov",
    "family",
    "corporate",
    "college_group",
    "delivery_first",
    "dine_in_first",
    "discount_sensitive",
    "complaint_recovery",
]
DietaryPreference = Literal["vegetarian", "non_vegetarian", "vegan", "jain", "no_preference"]
SpicePreference = Literal["mild", "medium", "spicy", "extra_spicy"]
NoteType = Literal[
    "general",
    "service_preference",
    "complaint",
    "recovery",
    "corporate",
    "delivery",
    "reservation",
    "dietary",
]
ConsentType = Literal[
    "whatsapp_marketing",
    "email_marketing",
    "sms_marketing",
    "loyalty",
    "feedback_request",
    "personalization",
]
ConsentStatus = Literal["granted", "withdrawn", "unknown"]


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


class CustomerCreateIn(BaseModel):
    customer_type: CustomerType = "individual"
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    organization_name: str | None = Field(default=None, max_length=180)
    display_name: str | None = Field(default=None, max_length=200)
    primary_phone_e164: str | None = Field(default=None, max_length=32)
    primary_email: str | None = Field(default=None, max_length=255)
    date_of_birth: date | None = None
    anniversary_date: date | None = None
    preferred_language: str | None = Field(default=None, max_length=16)
    dietary_preference: DietaryPreference | None = None
    spice_preference: SpicePreference | None = None
    customer_segment: CustomerSegment | None = None
    acquisition_source: str | None = Field(default=None, max_length=64)
    assigned_staff_id: uuid.UUID | None = None

    @field_validator("primary_phone_e164")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("primary_email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class CustomerUpdateIn(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    organization_name: str | None = Field(default=None, max_length=180)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    primary_phone_e164: str | None = Field(default=None, max_length=32)
    primary_email: str | None = Field(default=None, max_length=255)
    date_of_birth: date | None = None
    anniversary_date: date | None = None
    preferred_language: str | None = Field(default=None, max_length=16)
    dietary_preference: DietaryPreference | None = None
    spice_preference: SpicePreference | None = None
    customer_segment: CustomerSegment | None = None
    acquisition_source: str | None = Field(default=None, max_length=64)
    expected_version: int | None = None

    @field_validator("primary_phone_e164")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("primary_email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class CustomerAssignIn(BaseModel):
    assigned_staff_id: uuid.UUID | None = None


class CustomerArchiveIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CustomerListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_number: str
    display_name: str
    customer_type: str
    primary_phone_e164: str | None
    primary_email: str | None
    customer_status: str
    customer_segment: str | None
    assigned_staff_id: uuid.UUID | None
    completed_order_count: int
    lifetime_value_minor: int
    last_order_at: datetime | None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_number: str
    customer_type: str
    first_name: str | None
    last_name: str | None
    organization_name: str | None
    display_name: str
    primary_phone_e164: str | None
    primary_email: str | None
    date_of_birth: date | None
    anniversary_date: date | None
    preferred_language: str | None
    dietary_preference: str | None
    spice_preference: str | None
    customer_status: str
    customer_segment: str | None
    acquisition_source: str | None
    assigned_staff_id: uuid.UUID | None
    first_order_at: datetime | None
    last_order_at: datetime | None
    completed_order_count: int
    lifetime_value_minor: int
    average_order_value_minor: int
    last_activity_at: datetime | None
    merged_into_customer_id: uuid.UUID | None
    version: int
    created_at: datetime
    updated_at: datetime


class CustomerAddressIn(BaseModel):
    label: str | None = Field(default=None, max_length=64)
    recipient_name: str | None = Field(default=None, max_length=160)
    phone_e164: str | None = Field(default=None, max_length=32)
    address_line1: str = Field(min_length=1, max_length=200)
    address_line2: str | None = Field(default=None, max_length=200)
    landmark: str | None = Field(default=None, max_length=160)
    locality: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=16)
    country: str = Field(default="India", max_length=100)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    delivery_instructions: str | None = None
    is_default: bool = False

    @field_validator("phone_e164")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)


class CustomerAddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    label: str | None
    recipient_name: str | None
    phone_e164: str | None
    address_line1: str
    address_line2: str | None
    landmark: str | None
    locality: str | None
    city: str
    state: str
    postal_code: str
    country: str
    latitude: Decimal | None
    longitude: Decimal | None
    delivery_instructions: str | None
    is_default: bool
    is_active: bool


class CustomerNoteIn(BaseModel):
    note_type: NoteType = "general"
    content: str = Field(min_length=1)
    is_sensitive: bool = False


class CustomerNoteUpdateIn(BaseModel):
    content: str = Field(min_length=1)


class CustomerNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    note_type: str
    content: str
    is_sensitive: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
    updated_by: uuid.UUID | None


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    normalized_name: str
    description: str | None
    is_active: bool


class CustomerTagAddIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class TimelineEntryOut(BaseModel):
    id: uuid.UUID
    action_code: str
    actor_id: uuid.UUID | None
    created_at: datetime
    safe_metadata: dict[str, object] | None


class CustomerConsentSetIn(BaseModel):
    status: ConsentStatus
    source: str = Field(min_length=1, max_length=64)
    policy_version: str | None = Field(default=None, max_length=64)
    captured_text: str | None = None


class CustomerConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    consent_type: str
    status: str
    source: str
    policy_version: str | None
    granted_at: datetime | None
    withdrawn_at: datetime | None


class DuplicateMatchOut(BaseModel):
    customer: CustomerListItemOut
    match_reasons: list[str]


class MergeFieldResolution(BaseModel):
    field: str
    value: str | None = None


class MergePreviewIn(BaseModel):
    source_customer_id: uuid.UUID
    surviving_customer_id: uuid.UUID


class MergePreviewOut(BaseModel):
    source: CustomerOut
    surviving: CustomerOut
    conflicting_fields: list[str]
    source_address_count: int
    source_tag_count: int
    source_note_count: int


class MergeExecuteIn(BaseModel):
    source_customer_id: uuid.UUID
    surviving_customer_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=500)
    field_resolutions: list[MergeFieldResolution] = Field(default_factory=list)
