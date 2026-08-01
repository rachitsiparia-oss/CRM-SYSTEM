from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AnomalyRuleType = Literal[
    "absolute_threshold",
    "pct_change_prior_period",
    "rolling_average_deviation",
    "count_rate_threshold",
    "consecutive_deterioration",
    "missing_activity",
]
AnomalyComparisonOperator = Literal["gt", "gte", "lt", "lte"]
AnomalySeverity = Literal["low", "medium", "high", "critical"]
AnomalyFindingStatus = Literal["open", "acknowledged", "investigating", "resolved", "dismissed"]


class AnomalyRuleCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    metric_code: str
    rule_type: AnomalyRuleType
    comparison_operator: AnomalyComparisonOperator | None = None
    threshold_value: Decimal | None = None
    rolling_window_periods: int | None = Field(default=None, ge=1)
    minimum_sample_size: int = Field(default=1, ge=1)
    cooldown_hours: int = Field(default=24, ge=0)
    severity: AnomalySeverity = "medium"
    is_active: bool = True
    notify_task: bool = False
    notify_role_code: str | None = None


class AnomalyRuleUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    comparison_operator: AnomalyComparisonOperator | None = None
    threshold_value: Decimal | None = None
    rolling_window_periods: int | None = Field(default=None, ge=1)
    minimum_sample_size: int | None = Field(default=None, ge=1)
    cooldown_hours: int | None = Field(default=None, ge=0)
    severity: AnomalySeverity | None = None
    is_active: bool | None = None
    notify_task: bool | None = None
    notify_role_code: str | None = None


class AnomalyRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    metric_code: str
    rule_type: AnomalyRuleType
    comparison_operator: AnomalyComparisonOperator | None
    threshold_value: Decimal | None
    rolling_window_periods: int | None
    minimum_sample_size: int
    cooldown_hours: int
    severity: AnomalySeverity
    is_active: bool
    notify_task: bool
    notify_role_code: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class AnomalyFindingTransitionIn(BaseModel):
    target_status: AnomalyFindingStatus
    resolution_note: str | None = Field(default=None, max_length=2000)


class AnomalyFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    anomaly_rule_id: uuid.UUID
    metric_code: str
    dedup_key: str
    baseline_window_start: datetime | None
    baseline_window_end: datetime | None
    observed_window_start: datetime
    observed_window_end: datetime
    observed_value: Decimal | None
    expected_value: Decimal | None
    deviation_pct: Decimal | None
    severity: AnomalySeverity
    status: AnomalyFindingStatus
    evidence: dict[str, object] | None
    acknowledged_by: uuid.UUID | None
    acknowledged_at: datetime | None
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    resolution_note: str | None
    linked_task_id: uuid.UUID | None
    created_at: datetime
