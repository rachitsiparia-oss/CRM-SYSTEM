from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReportingArea = Literal[
    "executive",
    "sales",
    "orders",
    "customers",
    "leads",
    "reservations",
    "menu_products",
    "inventory_suppliers",
    "marketing",
    "loyalty",
    "feedback",
    "complaints",
    "communication",
    "staff_tasks",
    "system_operations",
]
ReportWindowCode = Literal[
    "today",
    "yesterday",
    "current_week",
    "previous_week",
    "current_month",
    "previous_month",
    "current_quarter",
    "previous_quarter",
    "custom",
]
ReportDefinitionType = Literal["system", "custom"]
ReportDefinitionVisibility = Literal["private", "shared", "system"]
ReportSharePermissionLevel = Literal["view", "run"]
ReportRunStatus = Literal["pending", "running", "completed", "failed"]
ReportRunTriggerSource = Literal["manual", "scheduled", "system"]
MetricValueType = Literal["count", "currency_minor", "percent", "decimal", "duration_minutes"]
MetricFreshness = Literal["live", "near_real_time", "cached", "scheduled"]


class MetricDefOut(BaseModel):
    code: str
    display_name: str
    description: str
    domain: ReportingArea
    value_type: MetricValueType
    unit: str | None
    required_permission: str
    supports_comparison: bool
    freshness: MetricFreshness
    version: int


class MetricResultOut(BaseModel):
    metric_code: str
    display_name: str
    value_type: MetricValueType
    unit: str | None
    value: float
    comparison_value: float | None
    change_pct: float | None
    window_code: str
    window_start: datetime
    window_end: datetime
    comparison_start: datetime | None
    comparison_end: datetime | None
    freshness: MetricFreshness
    generated_at: datetime


class DashboardOut(BaseModel):
    domain: str
    window_code: str
    window_start: datetime
    window_end: datetime
    metrics: list[MetricResultOut]
    partial_failures: list[str] = Field(default_factory=list)


class ReportDefinitionCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    domain: ReportingArea
    metric_codes: list[str] = Field(min_length=1, max_length=25)
    dimensions: list[str] | None = None
    default_filters: dict[str, object] | None = None
    default_window: ReportWindowCode = "current_month"
    comparison_enabled: bool = True
    visibility: ReportDefinitionVisibility = "private"


class ReportDefinitionUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    metric_codes: list[str] | None = Field(default=None, min_length=1, max_length=25)
    dimensions: list[str] | None = None
    default_filters: dict[str, object] | None = None
    default_window: ReportWindowCode | None = None
    comparison_enabled: bool | None = None
    visibility: ReportDefinitionVisibility | None = None
    is_active: bool | None = None


class ReportDefinitionShareIn(BaseModel):
    shared_with_staff_id: uuid.UUID | None = None
    shared_with_role_code: str | None = Field(default=None, max_length=64)
    permission_level: ReportSharePermissionLevel = "view"


class ReportDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    domain: ReportingArea
    definition_type: ReportDefinitionType
    metric_codes: list[str]
    dimensions: list[str] | None
    default_filters: dict[str, object] | None
    default_window: ReportWindowCode
    comparison_enabled: bool
    owner_staff_id: uuid.UUID | None
    visibility: ReportDefinitionVisibility
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ReportDefinitionShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_definition_id: uuid.UUID
    shared_with_staff_id: uuid.UUID | None
    shared_with_role_code: str | None
    permission_level: ReportSharePermissionLevel
    created_at: datetime


class ReportRunRequestIn(BaseModel):
    window_code: ReportWindowCode = "current_month"
    custom_start: datetime | None = None
    custom_end: datetime | None = None


class ReportRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_definition_id: uuid.UUID
    requested_by_staff_id: uuid.UUID | None
    trigger_source: ReportRunTriggerSource
    status: ReportRunStatus
    window_code: str
    window_start: datetime
    window_end: datetime
    comparison_window_start: datetime | None
    comparison_window_end: datetime | None
    timezone: str
    row_count: int | None
    checksum_sha256: str | None
    started_at: datetime | None
    completed_at: datetime | None
    failure_details: str | None
    created_at: datetime


class ReportRunDetailOut(BaseModel):
    run: ReportRunOut
    metrics: list[MetricResultOut]
    summary: dict[str, object] | None


class DrilldownRecordOut(BaseModel):
    record_type: str
    record_id: str
    label: str
    detail: dict[str, object]


class DrilldownOut(BaseModel):
    metric_code: str
    window_code: str
    window_start: datetime
    window_end: datetime
    records: list[DrilldownRecordOut]
    truncated: bool
