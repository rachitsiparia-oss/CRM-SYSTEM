import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TaskSource = Literal[
    "manual",
    "reservation_followup",
    "order_issue",
    "lead_followup",
    "inventory_alert",
    "system",
    "recurring",
]
TaskPriority = Literal["low", "normal", "high", "urgent"]
TaskStatus = Literal["open", "in_progress", "blocked", "completed", "cancelled"]
TaskRelatedType = Literal[
    "customer", "lead", "order", "reservation", "conversation", "inventory_item"
]


class RecurrenceRule(BaseModel):
    frequency: Literal["daily", "weekly", "monthly"]
    interval: int = Field(default=1, ge=1)
    days_of_week: list[int] | None = None
    end_date: datetime | None = None


class TaskCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    source: TaskSource = "manual"
    priority: TaskPriority = "normal"
    due_at: datetime | None = None
    assigned_staff_id: uuid.UUID | None = None
    assigned_department_id: uuid.UUID | None = None
    related_type: TaskRelatedType | None = None
    related_id: uuid.UUID | None = None
    is_recurring_template: bool = False
    recurrence_rule: RecurrenceRule | None = None
    idempotency_key: str | None = Field(default=None, max_length=160)


class TaskUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    version: int


class TaskTransitionIn(BaseModel):
    target_status: TaskStatus
    reason: str | None = None
    completion_notes: str | None = None
    blocked_reason: str | None = None


class TaskAssignIn(BaseModel):
    assigned_staff_id: uuid.UUID | None = None
    assigned_department_id: uuid.UUID | None = None
    reason: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_number: str
    title: str
    description: str | None
    source: str
    priority: str
    status: str
    due_at: datetime | None
    assigned_staff_id: uuid.UUID | None
    assigned_department_id: uuid.UUID | None
    completed_at: datetime | None
    completed_by: uuid.UUID | None
    completion_notes: str | None
    blocked_reason: str | None
    related_type: str | None
    related_id: uuid.UUID | None
    is_recurring_template: bool
    recurrence_rule: dict[str, Any] | None
    parent_task_id: uuid.UUID | None
    version: int
    created_at: datetime
    updated_at: datetime
