import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.normalization import NormalizationError, normalize_email, normalize_phone


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


TableStatus = Literal[
    "available", "reserved", "occupied", "cleaning", "blocked", "maintenance", "merged"
]
TableShape = Literal["round", "square", "rectangle", "oval", "booth", "bar", "custom"]
TableBlockType = Literal["cleaning", "maintenance", "private_event", "other"]


def _validated_code(value: str) -> str:
    stripped = value.strip().lower()
    if not stripped:
        raise ValueError("Code cannot be empty.")
    if not all(c.isalnum() or c in "-_" for c in stripped):
        raise ValueError("Code may only contain letters, numbers, hyphens, and underscores.")
    return stripped


ReservationSource = Literal["phone", "walk_in", "online", "whatsapp", "staff"]
ReservationStatus = Literal[
    "requested",
    "pending_review",
    "needs_clarification",
    "approved",
    "rejected",
    "confirmation_sending",
    "confirmed",
    "reminder_scheduled",
    "arrived",
    "seated",
    "completed",
    "no_show",
    "cancelled_by_customer",
    "cancelled_by_restaurant",
    "expired",
]
CancellationSource = Literal["customer", "restaurant"]
ReservationNoteType = Literal[
    "internal",
    "kitchen",
    "guest_preference",
    "allergy",
    "special_occasion",
    "accessibility",
    "celebration",
    "vip",
]


class ReservationCreateIn(BaseModel):
    customer_id: uuid.UUID | None = None
    guest_name: str = Field(min_length=1, max_length=180)
    phone_e164: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    party_size: int = Field(ge=1)
    reservation_date: date
    start_time: time
    end_time: time | None = None
    dining_area_id: uuid.UUID | None = None
    source: ReservationSource
    special_requests: str | None = None
    deposit_required: bool = False
    deposit_amount_minor: int | None = Field(default=None, ge=0)
    idempotency_key: str = Field(min_length=1, max_length=160)

    @field_validator("phone_e164")
    @classmethod
    def _validate_phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class ReservationUpdateIn(BaseModel):
    customer_id: uuid.UUID | None = None
    guest_name: str | None = Field(default=None, min_length=1, max_length=180)
    phone_e164: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    party_size: int | None = Field(default=None, ge=1)
    reservation_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    dining_area_id: uuid.UUID | None = None
    special_requests: str | None = None
    deposit_required: bool | None = None
    deposit_amount_minor: int | None = Field(default=None, ge=0)
    expected_version: int | None = None

    @field_validator("phone_e164")
    @classmethod
    def _validate_phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class ReservationTransitionIn(BaseModel):
    new_status: ReservationStatus
    reason: str | None = Field(default=None, max_length=500)


class ReservationApprovalIn(BaseModel):
    approve: bool
    reason: str | None = Field(default=None, max_length=500)


class ReservationNoteIn(BaseModel):
    note_type: ReservationNoteType = "internal"
    content: str = Field(min_length=1)
    is_internal: bool = True


class ReservationTagAssignIn(BaseModel):
    tag_id: uuid.UUID


class ArchiveIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class WalkInCreateIn(BaseModel):
    guest_name: str = Field(min_length=1, max_length=180)
    phone_e164: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    party_size: int = Field(ge=1)
    dining_area_id: uuid.UUID | None = None
    special_requests: str | None = None

    @field_validator("phone_e164")
    @classmethod
    def _validate_phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_number: str
    customer_id: uuid.UUID | None
    guest_name: str
    phone_e164: str | None
    email: str | None
    party_size: int
    reservation_date: date
    start_time: time
    end_time: time | None
    dining_area_id: uuid.UUID | None
    status: str
    source: str
    is_walk_in: bool
    special_requests: str | None
    order_id: uuid.UUID | None
    assigned_staff_id: uuid.UUID | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejected_by: uuid.UUID | None
    rejected_at: datetime | None
    rejection_reason: str | None
    arrived_at: datetime | None
    seated_at: datetime | None
    completed_at: datetime | None
    no_show_at: datetime | None
    cancelled_at: datetime | None
    cancellation_source: str | None
    cancellation_reason: str | None
    expires_at: datetime | None
    deposit_required: bool
    deposit_amount_minor: int | None
    version: int
    created_at: datetime
    updated_at: datetime


class ReservationStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_id: uuid.UUID
    previous_status: str | None
    new_status: str
    actor_id: uuid.UUID | None
    reason: str | None
    created_at: datetime


class ReservationTimelineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_id: uuid.UUID
    event_type: str
    summary: str
    event_metadata: dict[str, object] | None
    performed_by: uuid.UUID | None
    occurred_at: datetime


class ReservationNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_id: uuid.UUID
    note_type: str
    content: str
    is_internal: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
    updated_by: uuid.UUID | None


# --- Dining areas -------------------------------------------------------


class DiningAreaCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        return _validated_code(v)


class DiningAreaUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    is_active: bool | None = None
    expected_version: int | None = None


class DiningAreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    version: int


# --- Restaurant tables ----------------------------------------------------


class RestaurantTableCreateIn(BaseModel):
    dining_area_id: uuid.UUID
    table_number: str = Field(min_length=1, max_length=20)
    capacity: int = Field(ge=1)
    minimum_capacity: int | None = Field(default=None, ge=1)
    maximum_capacity: int | None = Field(default=None, ge=1)
    shape: TableShape = "square"
    is_wheelchair_accessible: bool = False
    is_temporary: bool = False
    qr_identifier: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    sort_order: int = Field(default=0, ge=0)


class RestaurantTableUpdateIn(BaseModel):
    dining_area_id: uuid.UUID | None = None
    capacity: int | None = Field(default=None, ge=1)
    minimum_capacity: int | None = Field(default=None, ge=1)
    maximum_capacity: int | None = Field(default=None, ge=1)
    shape: TableShape | None = None
    is_wheelchair_accessible: bool | None = None
    is_temporary: bool | None = None
    qr_identifier: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    is_active: bool | None = None
    expected_version: int | None = None


class TableStatusTransitionIn(BaseModel):
    new_status: TableStatus
    reason: str | None = Field(default=None, max_length=500)


class TableMergeIn(BaseModel):
    secondary_table_ids: list[uuid.UUID] = Field(min_length=1)
    reason: str | None = Field(default=None, max_length=500)


class TableSplitIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class TableBlockCreateIn(BaseModel):
    block_type: TableBlockType
    starts_at: datetime
    ends_at: datetime
    reason: str | None = None


class RestaurantTableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dining_area_id: uuid.UUID
    table_number: str
    capacity: int
    minimum_capacity: int | None
    maximum_capacity: int | None
    shape: str
    status: str
    is_wheelchair_accessible: bool
    is_temporary: bool
    merged_with_table_id: uuid.UUID | None
    qr_identifier: str | None
    notes: str | None
    is_active: bool
    sort_order: int
    version: int


class TableStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    restaurant_table_id: uuid.UUID
    previous_status: str | None
    new_status: str
    reason: str | None
    event_metadata: dict[str, object] | None
    changed_by: uuid.UUID | None
    created_at: datetime


class TableBlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    restaurant_table_id: uuid.UUID
    block_type: str
    starts_at: datetime
    ends_at: datetime
    reason: str | None
    is_active: bool
    released_by: uuid.UUID | None
    released_at: datetime | None


# --- Table assignment -------------------------------------------------------


class TableAssignIn(BaseModel):
    table_ids: list[uuid.UUID] = Field(min_length=1)


class ReservationTableAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_id: uuid.UUID
    restaurant_table_id: uuid.UUID
    assigned_at: datetime
    assigned_by: uuid.UUID | None
    unassigned_at: datetime | None


# --- Waitlist ----------------------------------------------------------------


class WaitlistCreateIn(BaseModel):
    customer_id: uuid.UUID | None = None
    guest_name: str = Field(min_length=1, max_length=180)
    phone_e164: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    party_size: int = Field(ge=1)
    dining_area_id: uuid.UUID | None = None
    priority: int = 0
    estimated_wait_minutes: int | None = Field(default=None, ge=0)
    notes: str | None = None

    @field_validator("phone_e164")
    @classmethod
    def _validate_phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class WaitlistPromoteIn(BaseModel):
    reservation_id: uuid.UUID


class WaitlistCancelIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class WaitlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID | None
    guest_name: str
    phone_e164: str | None
    email: str | None
    party_size: int
    dining_area_id: uuid.UUID | None
    priority: int
    status: str
    requested_at: datetime
    estimated_wait_minutes: int | None
    notified_at: datetime | None
    promoted_reservation_id: uuid.UUID | None
    resolved_at: datetime | None
    notes: str | None
    version: int


# --- Customer-360 reservation stats ------------------------------------------


class CustomerReservationStatsOut(BaseModel):
    lifetime_visit_count: int
    no_show_count: int
    cancellation_count: int
    average_party_size: float | None
    last_visit_at: datetime | None
    preferred_dining_area_id: uuid.UUID | None
    preferred_table_id: uuid.UUID | None
    preferred_start_time: time | None


# --- Business hours, holidays, and policies ----------------------------------


class BusinessHoursUpdateIn(BaseModel):
    is_closed: bool
    opens_at: time | None = None
    closes_at: time | None = None
    closes_next_day: bool = False
    break_starts_at: time | None = None
    break_ends_at: time | None = None
    notes: str | None = None
    expected_version: int | None = None


class BusinessHoursOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    day_of_week: int
    is_closed: bool
    opens_at: time | None
    closes_at: time | None
    closes_next_day: bool
    break_starts_at: time | None
    break_ends_at: time | None
    notes: str | None
    version: int


class HolidayCalendarCreateIn(BaseModel):
    holiday_date: date
    name: str = Field(min_length=1, max_length=120)
    is_closed: bool = True
    opens_at: time | None = None
    closes_at: time | None = None
    notes: str | None = None


class HolidayCalendarUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_closed: bool | None = None
    opens_at: time | None = None
    closes_at: time | None = None
    notes: str | None = None
    expected_version: int | None = None


class HolidayCalendarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    holiday_date: date
    name: str
    is_closed: bool
    opens_at: time | None
    closes_at: time | None
    notes: str | None
    version: int


class ReservationPoliciesUpdateIn(BaseModel):
    deposit_required_by_default: bool | None = None
    default_deposit_amount_minor: int | None = Field(default=None, ge=0)
    advance_booking_limit_days: int | None = Field(default=None, gt=0)
    minimum_notice_minutes: int | None = Field(default=None, ge=0)
    cancellation_window_minutes: int | None = Field(default=None, ge=0)
    no_show_grace_minutes: int | None = Field(default=None, ge=0)
    buffer_before_minutes: int | None = Field(default=None, ge=0)
    buffer_after_minutes: int | None = Field(default=None, ge=0)
    default_minimum_party_size: int | None = Field(default=None, gt=0)
    default_maximum_party_size: int | None = Field(default=None, gt=0)
    large_party_threshold: int | None = Field(default=None, gt=0)
    expected_version: int | None = None


class ReservationPoliciesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deposit_required_by_default: bool
    default_deposit_amount_minor: int | None
    advance_booking_limit_days: int
    minimum_notice_minutes: int
    cancellation_window_minutes: int
    no_show_grace_minutes: int
    buffer_before_minutes: int
    buffer_after_minutes: int
    default_minimum_party_size: int
    default_maximum_party_size: int
    large_party_threshold: int
    version: int


class ReservationSettingsUpdateIn(BaseModel):
    default_reservation_duration_minutes: int | None = Field(default=None, gt=0)
    auto_assignment_enabled: bool | None = None
    waitlist_enabled: bool | None = None
    online_booking_enabled: bool | None = None
    walk_in_enabled: bool | None = None
    pending_request_expiry_minutes: int | None = Field(default=None, gt=0)
    reminder_lead_time_minutes: int | None = Field(default=None, gt=0)
    expected_version: int | None = None


class ReservationSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    default_reservation_duration_minutes: int
    auto_assignment_enabled: bool
    waitlist_enabled: bool
    online_booking_enabled: bool
    walk_in_enabled: bool
    pending_request_expiry_minutes: int | None
    reminder_lead_time_minutes: int | None
    version: int


# --- Order linkage ------------------------------------------------------


class ReservationOrderLinkIn(BaseModel):
    order_id: uuid.UUID


# --- Dashboard -----------------------------------------------------------


class ReservationDashboardStatsOut(BaseModel):
    target_date: date
    total_count: int
    upcoming_count: int
    completed_count: int
    cancelled_count: int
    no_show_count: int
    walk_in_count: int
    average_party_size: float | None
    average_dining_duration_minutes: float | None
    conversion_rate: float | None
    hourly_reservation_counts: dict[int, int]
    dining_area_utilization: dict[str, int]
    table_utilization: dict[str, int]
