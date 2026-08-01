from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ScheduleFrequency = Literal["daily", "weekly", "monthly"]
ExportFormat = Literal["csv", "xlsx", "pdf"]
DeliveryStatus = Literal["pending", "sent", "delivered", "failed"]


class ScheduledReportCreateIn(BaseModel):
    report_definition_id: uuid.UUID
    name: str = Field(min_length=1, max_length=160)
    schedule_frequency: ScheduleFrequency
    schedule_day_of_week: int | None = Field(default=None, ge=0, le=6)
    schedule_day_of_month: int | None = Field(default=None, ge=1, le=28)
    schedule_time_of_day: time = time(6, 0)
    timezone: str = "Asia/Kolkata"
    output_format: ExportFormat = "pdf"
    fixed_filters: dict[str, object] | None = None
    include_ai_narrative: bool = False

    @model_validator(mode="after")
    def _validate_schedule_shape(self) -> ScheduledReportCreateIn:
        if self.schedule_frequency == "weekly" and self.schedule_day_of_week is None:
            raise ValueError("schedule_day_of_week is required for a weekly schedule.")
        if self.schedule_frequency == "monthly" and self.schedule_day_of_month is None:
            raise ValueError("schedule_day_of_month is required for a monthly schedule.")
        return self


class ScheduledReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_definition_id: uuid.UUID
    name: str
    schedule_frequency: ScheduleFrequency
    schedule_day_of_week: int | None
    schedule_day_of_month: int | None
    schedule_time_of_day: time
    timezone: str
    output_format: ExportFormat
    fixed_filters: dict[str, object] | None
    include_ai_narrative: bool
    is_enabled: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ScheduledReportRecipientCreateIn(BaseModel):
    recipient_staff_id: uuid.UUID | None = None
    recipient_role_code: str | None = Field(default=None, max_length=64)
    recipient_email_override: str | None = Field(default=None, max_length=320)

    @model_validator(mode="after")
    def _validate_exactly_one_target(self) -> ScheduledReportRecipientCreateIn:
        targets = [
            self.recipient_staff_id,
            self.recipient_role_code,
            self.recipient_email_override,
        ]
        if sum(1 for t in targets if t is not None) != 1:
            raise ValueError(
                "Exactly one of recipient_staff_id, recipient_role_code, or "
                "recipient_email_override must be set."
            )
        return self


class ScheduledReportRecipientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheduled_report_id: uuid.UUID
    recipient_staff_id: uuid.UUID | None
    recipient_role_code: str | None
    recipient_email_override: str | None
    created_at: datetime


class SetEnabledIn(BaseModel):
    is_enabled: bool


class ReportDeliveryAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheduled_report_id: uuid.UUID
    report_run_id: uuid.UUID | None
    export_artifact_id: uuid.UUID | None
    occurrence_key: str
    recipient_reference: str
    delivery_channel: str
    status: DeliveryStatus
    attempted_at: datetime | None
    failure_details: str | None
    created_at: datetime
