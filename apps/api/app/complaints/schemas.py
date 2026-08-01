from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ComplaintSourceType = Literal[
    "feedback", "direct", "conversation", "staff_entry", "order", "reservation", "other"
]
ComplaintCategory = Literal[
    "food_quality",
    "incorrect_item",
    "missing_item",
    "packaging",
    "delay",
    "delivery",
    "payment",
    "refund",
    "reservation",
    "staff_behavior",
    "cleanliness",
    "allergy_or_dietary",
    "promotion",
    "loyalty",
    "communication",
    "corporate_order",
    "other",
]
ComplaintSeverity = Literal["low", "medium", "high", "critical"]
ComplaintPriority = Literal["low", "normal", "high", "urgent"]
ComplaintStatus = Literal[
    "new",
    "acknowledged",
    "investigating",
    "awaiting_customer",
    "awaiting_internal",
    "resolution_proposed",
    "resolved",
    "closed",
    "reopened",
    "cancelled",
]
RootCauseCategory = Literal[
    "process_failure",
    "preparation_error",
    "inventory_unavailable",
    "packaging_error",
    "delivery_delay",
    "staff_training_gap",
    "communication_failure",
    "system_failure",
    "supplier_issue",
    "policy_gap",
    "customer_expectation_mismatch",
    "unknown",
]
ComplaintLinkRelationshipType = Literal["duplicate_of", "related_to"]
FollowUpOutcome = Literal["satisfied", "unsatisfied", "no_response", "escalated_again"]


class ComplaintCreateIn(BaseModel):
    customer_id: uuid.UUID
    source_type: ComplaintSourceType
    feedback_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    category: ComplaintCategory
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    severity: ComplaintSeverity
    priority: ComplaintPriority = "normal"
    channel: str | None = Field(default=None, max_length=32)
    sla_policy_id: uuid.UUID | None = None


class ComplaintUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    category: ComplaintCategory | None = None
    severity: ComplaintSeverity | None = None
    priority: ComplaintPriority | None = None
    customer_visible_summary: str | None = None


class ComplaintTransitionIn(BaseModel):
    target_status: ComplaintStatus
    reason: str | None = None
    resolution_summary: str | None = None


class ComplaintAssignIn(BaseModel):
    assigned_staff_id: uuid.UUID | None = None
    assigned_department_id: uuid.UUID | None = None
    reason: str | None = None


class ComplaintEscalateIn(BaseModel):
    reason: str = Field(min_length=1)
    new_assigned_staff_id: uuid.UUID | None = None
    new_assigned_department_id: uuid.UUID | None = None


class RootCauseUpdateIn(BaseModel):
    root_cause: RootCauseCategory
    notes: str | None = None


class NoteCreateIn(BaseModel):
    note: str = Field(min_length=1)


class FollowUpCreateIn(BaseModel):
    scheduled_at: datetime
    notes: str | None = None


class FollowUpCompleteIn(BaseModel):
    outcome: FollowUpOutcome
    notes: str | None = None


class ComplaintLinkCreateIn(BaseModel):
    related_complaint_id: uuid.UUID
    relationship_type: ComplaintLinkRelationshipType


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_number: str
    customer_id: uuid.UUID
    source_type: ComplaintSourceType
    feedback_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    order_id: uuid.UUID | None
    reservation_id: uuid.UUID | None
    category: ComplaintCategory
    title: str
    description: str
    severity: ComplaintSeverity
    priority: ComplaintPriority
    status: ComplaintStatus
    channel: str | None
    assigned_staff_id: uuid.UUID | None
    assigned_department_id: uuid.UUID | None
    current_escalation_level: int
    sla_policy_id: uuid.UUID | None
    first_response_due_at: datetime | None
    acknowledgement_due_at: datetime | None
    resolution_due_at: datetime | None
    follow_up_due_at: datetime | None
    first_responded_at: datetime | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    reopened_at: datetime | None
    reopened_count: int
    customer_sentiment: str | None
    root_cause: RootCauseCategory | None
    resolution_summary: str | None
    customer_visible_summary: str | None
    is_hr_sensitive: bool
    created_at: datetime
    updated_at: datetime


class ComplaintStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: ComplaintStatus | None
    to_status: ComplaintStatus
    actor_id: uuid.UUID | None
    reason: str | None
    created_at: datetime


class ComplaintAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assigned_staff_id: uuid.UUID | None
    assigned_department_id: uuid.UUID | None
    assigned_by: uuid.UUID | None
    reason: str | None
    created_at: datetime


class ComplaintNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_staff_id: uuid.UUID
    note: str
    created_at: datetime


class ComplaintEscalationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    level: int
    reason: str
    triggered_by_staff_id: uuid.UUID | None
    new_assigned_staff_id: uuid.UUID | None
    new_assigned_department_id: uuid.UUID | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime


class ComplaintFollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheduled_at: datetime
    completed_at: datetime | None
    outcome: FollowUpOutcome | None
    notes: str | None
    created_at: datetime


class ComplaintLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_id: uuid.UUID
    related_complaint_id: uuid.UUID
    relationship_type: ComplaintLinkRelationshipType
    created_at: datetime


class TimelineEntryOut(BaseModel):
    """A single, uniformly-shaped read-time aggregation row — CLAUDE.md
    section 12.3's "Build the timeline as a read-time aggregation... Do not
    create a redundant generic timeline table"."""

    entry_type: Literal[
        "status_change",
        "assignment",
        "note",
        "attachment",
        "escalation",
        "follow_up",
        "recovery_action",
        "root_cause_change",
    ]
    occurred_at: datetime
    actor_id: uuid.UUID | None
    summary: str
    detail: dict[str, object]


class SlaPolicyCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    applicable_categories: list[ComplaintCategory] | None = None
    applicable_severities: list[ComplaintSeverity] | None = None
    first_response_minutes: int = Field(gt=0)
    acknowledgement_minutes: int = Field(gt=0)
    resolution_minutes: int = Field(gt=0)
    follow_up_minutes: int | None = Field(default=None, gt=0)
    escalation_after_minutes: int | None = Field(default=None, gt=0)
    business_hours_only: bool = True
    default_assignee_department_id: uuid.UUID | None = None


class SlaPolicyUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None
    applicable_categories: list[ComplaintCategory] | None = None
    applicable_severities: list[ComplaintSeverity] | None = None
    first_response_minutes: int | None = Field(default=None, gt=0)
    acknowledgement_minutes: int | None = Field(default=None, gt=0)
    resolution_minutes: int | None = Field(default=None, gt=0)
    follow_up_minutes: int | None = Field(default=None, gt=0)
    escalation_after_minutes: int | None = Field(default=None, gt=0)
    business_hours_only: bool | None = None
    default_assignee_department_id: uuid.UUID | None = None


class SlaPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    is_active: bool
    applicable_categories: list[str] | None
    applicable_severities: list[str] | None
    first_response_minutes: int
    acknowledgement_minutes: int
    resolution_minutes: int
    follow_up_minutes: int | None
    escalation_after_minutes: int | None
    business_hours_only: bool
    default_assignee_department_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ComplaintAnalyticsOut(BaseModel):
    open_count: int
    new_30d: int
    resolved_30d: int
    reopened_30d: int
    by_severity: list[dict[str, int | str]]
    by_category: list[dict[str, int | str]]
    average_first_response_minutes: float | None
    average_resolution_minutes: float | None
    sla_breach_rate_pct: float
    escalation_rate_pct: float
