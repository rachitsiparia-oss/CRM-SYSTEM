from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FeatureCode = Literal[
    "dashboard_summary",
    "metric_change_explanation",
    "anomaly_evidence_summary",
    "report_narrative",
    "nl_question_query_plan",
]
AiRequestStatus = Literal["pending", "completed", "failed", "blocked"]
AiFeedbackOutcome = Literal["accepted", "edited", "rejected", "ignored"]


class AiCompletionRequestIn(BaseModel):
    feature_code: FeatureCode
    params: dict[str, object] = Field(default_factory=dict)


class AiRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requested_by_staff_id: uuid.UUID
    feature_code: str
    prompt_template_version: int
    provider_code: str
    model_reference: str
    grounding_summary: dict[str, object] | None
    output_text: str | None
    output_structured: dict[str, object] | None
    status: AiRequestStatus
    failure_category: str | None
    safety_blocked: bool
    safety_block_reason: str | None
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime
    completed_at: datetime | None


class AiSourceReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: str
    source_id: str
    source_label: str | None


class AiRequestFeedbackIn(BaseModel):
    outcome_state: AiFeedbackOutcome
    edited_content: str | None = Field(default=None, max_length=8000)
    rating: int | None = Field(default=None, ge=1, le=5)
    feedback_note: str | None = Field(default=None, max_length=2000)


class AiRequestFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ai_request_id: uuid.UUID
    staff_id: uuid.UUID
    outcome_state: AiFeedbackOutcome
    edited_content: str | None
    rating: int | None
    feedback_note: str | None
    created_at: datetime
