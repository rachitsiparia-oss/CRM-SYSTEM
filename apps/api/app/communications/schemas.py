import uuid
from datetime import date, datetime, time
from typing import Any, Literal

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


ConversationStatus = Literal[
    "open",
    "pending",
    "waiting_on_customer",
    "waiting_on_staff",
    "snoozed",
    "resolved",
    "closed",
    "spam",
]
ConversationPriority = Literal["low", "normal", "high", "urgent"]
MessageDirection = Literal["inbound", "outbound", "internal"]
MessageType = Literal[
    "text",
    "email",
    "sms",
    "whatsapp",
    "system_event",
    "template",
    "internal_note",
    "attachment",
    "reservation_update",
    "order_update",
    "feedback_request",
]
TemplateCategory = Literal[
    "reservation_confirmation",
    "reservation_reminder",
    "reservation_cancellation",
    "reservation_modification",
    "waitlist_update",
    "table_ready",
    "order_confirmation",
    "order_ready",
    "order_cancellation",
    "feedback_request",
    "lead_follow_up",
    "birthday",
    "anniversary",
    "general",
]
TemplateStatus = Literal["draft", "active", "archived"]
ScheduledMessagePurpose = Literal[
    "reservation_reminder", "feedback_request", "lead_follow_up", "manual"
]
SuppressionDestinationType = Literal["email", "phone"]
SuppressionReason = Literal[
    "hard_bounce",
    "spam_complaint",
    "invalid_destination",
    "manual_block",
    "customer_request",
    "unsubscribed",
]
SuppressionScope = Literal["all", "promotional_only"]
CallDirection = Literal["inbound", "outbound"]
CallOutcome = Literal["connected", "no_answer", "voicemail", "busy", "wrong_number", "other"]


class CommunicationChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    provider: str | None
    default_sender_identity: str | None
    is_enabled: bool
    inbound_enabled: bool
    outbound_enabled: bool
    requires_template: bool
    business_hours_restricted: bool
    rate_limit_per_minute: int | None
    fallback_channel_id: uuid.UUID | None
    sort_order: int


class CommunicationChannelUpdateIn(BaseModel):
    is_enabled: bool | None = None
    inbound_enabled: bool | None = None
    outbound_enabled: bool | None = None
    default_sender_identity: str | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=0)
    fallback_channel_id: uuid.UUID | None = None


class ConversationCreateIn(BaseModel):
    channel_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    guest_name: str | None = Field(default=None, max_length=180)
    phone_e164: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=254)
    subject: str | None = Field(default=None, max_length=200)
    priority: ConversationPriority = "normal"
    initial_message_body: str | None = None

    @field_validator("phone_e164")
    @classmethod
    def _validate_phone(cls, v: str | None) -> str | None:
        return _validated_phone(v)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        return _validated_email(v)


class ConversationTransitionIn(BaseModel):
    target_status: ConversationStatus
    reason: str | None = None
    snoozed_until: datetime | None = None
    spam_reason: str | None = None


class ConversationAssignIn(BaseModel):
    assignee_id: uuid.UUID | None = None
    reason: str | None = None


class ConversationPriorityIn(BaseModel):
    priority: ConversationPriority


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_number: str
    channel_id: uuid.UUID
    customer_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    guest_name: str | None
    phone_e164: str | None
    email: str | None
    subject: str | None
    status: str
    priority: str
    source: str
    assigned_staff_id: uuid.UUID | None
    last_inbound_at: datetime | None
    last_outbound_at: datetime | None
    last_activity_at: datetime | None
    first_response_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    snoozed_until: datetime | None
    unread_count: int
    version: int
    created_at: datetime
    updated_at: datetime


class MessageCreateIn(BaseModel):
    body_text: str | None = None
    subject: str | None = None
    message_type: MessageType = "text"
    template_id: uuid.UUID | None = None
    template_variables: dict[str, Any] | None = None
    recipient_reference: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)


class InternalNoteCreateIn(BaseModel):
    body_text: str = Field(min_length=1)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    channel_id: uuid.UUID
    direction: str
    message_type: str
    sender_reference: str | None
    recipient_reference: str | None
    subject: str | None
    body_text: str | None
    template_id: uuid.UUID | None
    provider_message_id: str | None
    reply_to_message_id: uuid.UUID | None
    delivery_status: str
    failure_code: str | None
    failure_reason: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    failed_at: datetime | None
    received_at: datetime | None
    retry_count: int
    created_by: uuid.UUID | None
    created_at: datetime


class MessageAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID
    file_name: str
    mime_type: str
    size_bytes: int
    upload_status: str
    scan_status: str
    created_at: datetime


class ConversationTimelineEntryOut(BaseModel):
    entry_type: Literal["message", "status_change", "assignment_change"]
    occurred_at: datetime
    payload: dict[str, Any]


class MessageTemplateCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=80)
    channel_id: uuid.UUID
    category: TemplateCategory
    language: str = Field(default="en", max_length=10)
    subject: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)
    is_transactional: bool = True
    effective_from: date | None = None
    effective_to: date | None = None


class MessageTemplateUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    subject: str | None = None
    body: str | None = None
    variables: list[str] | None = None
    status: TemplateStatus | None = None
    is_transactional: bool | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    version: int


class MessageTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    channel_id: uuid.UUID
    category: str
    language: str
    subject: str | None
    body: str
    variables: list[str]
    status: str
    provider_template_id: str | None
    is_transactional: bool
    effective_from: date | None
    effective_to: date | None
    version: int
    created_at: datetime
    updated_at: datetime


class TemplatePreviewIn(BaseModel):
    variables: dict[str, Any]


class TemplatePreviewOut(BaseModel):
    subject: str | None
    body: str


class ScheduledMessageCreateIn(BaseModel):
    purpose: ScheduledMessagePurpose
    template_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    channel_id: uuid.UUID
    recipient_reference: str = Field(min_length=1, max_length=200)
    scheduled_for: datetime
    timezone: str = "Asia/Kolkata"
    template_variables: dict[str, Any] | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)


class ScheduledMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purpose: str
    template_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    customer_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    channel_id: uuid.UUID
    recipient_reference: str
    scheduled_for: datetime
    timezone: str
    status: str
    cancelled_at: datetime | None
    attempt_count: int
    last_error: str | None
    result_message_id: uuid.UUID | None
    created_at: datetime


class CommunicationPreferenceUpdateIn(BaseModel):
    preferred_channel_id: uuid.UUID | None = None
    allow_transactional_email: bool | None = None
    allow_transactional_sms: bool | None = None
    allow_transactional_whatsapp: bool | None = None
    allow_promotional_email: bool | None = None
    allow_promotional_sms: bool | None = None
    allow_promotional_whatsapp: bool | None = None
    do_not_contact: bool | None = None
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    language_preference: str | None = Field(default=None, max_length=10)


class CommunicationPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    preferred_channel_id: uuid.UUID | None
    allow_transactional_email: bool
    allow_transactional_sms: bool
    allow_transactional_whatsapp: bool
    allow_promotional_email: bool
    allow_promotional_sms: bool
    allow_promotional_whatsapp: bool
    do_not_contact: bool
    quiet_hours_start: time | None
    quiet_hours_end: time | None
    language_preference: str


class CommunicationConsentCreateIn(BaseModel):
    customer_id: uuid.UUID
    consent_type: str
    consent_given: bool
    source: str
    consent_version: str | None = None


class CommunicationConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    consent_type: str
    consent_given: bool
    source: str
    consent_version: str | None
    actor_id: uuid.UUID | None
    created_at: datetime


class CommunicationSuppressionCreateIn(BaseModel):
    destination_type: SuppressionDestinationType
    destination_value: str = Field(min_length=1, max_length=200)
    reason: SuppressionReason
    scope: SuppressionScope = "all"
    suppressed_until: datetime | None = None
    customer_id: uuid.UUID | None = None
    notes: str | None = None


class CommunicationSuppressionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    destination_type: str
    destination_value: str
    reason: str
    scope: str
    suppressed_until: datetime | None
    is_active: bool
    customer_id: uuid.UUID | None
    notes: str | None
    lifted_at: datetime | None
    created_at: datetime


class ManualCallLogCreateIn(BaseModel):
    customer_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    direction: CallDirection
    started_at: datetime
    ended_at: datetime | None = None
    outcome: CallOutcome
    notes: str | None = None
    follow_up_required: bool = False
    related_reservation_id: uuid.UUID | None = None
    related_order_id: uuid.UUID | None = None


class ManualCallLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    staff_user_id: uuid.UUID
    direction: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    outcome: str
    notes: str | None
    follow_up_required: bool
    created_at: datetime


class CommunicationAnalyticsOut(BaseModel):
    open_conversations: int
    unread_conversations: int
    waiting_on_staff: int
    waiting_on_customer: int
    resolved_today: int
    average_first_response_seconds: float | None
    average_resolution_seconds: float | None
    messages_by_channel: dict[str, int]
    inbound_count: int
    outbound_count: int
    delivery_rate: float | None
    failure_rate: float | None
    suppression_count: int


class CustomerCommunicationStatsOut(BaseModel):
    open_conversation_count: int
    total_inbound_messages: int
    total_outbound_messages: int
    last_contact_at: datetime | None
    preferred_channel_id: uuid.UUID | None
    average_response_seconds: float | None
    unresolved_conversation_count: int
