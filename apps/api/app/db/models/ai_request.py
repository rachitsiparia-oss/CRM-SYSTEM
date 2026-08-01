import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    AppendOnlyTimestampMixin,
    AuditedMixin,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

# GROWTH_AND_INTELLIGENCE.md section 14.2 — the closed capability list. AI
# is never allowed a feature code outside this set (section 14.3's
# prohibited-behavior list is enforced by simply never defining a mutating
# capability here, not by a runtime blocklist).
AI_FEATURE_CODES = (
    "customer_history_summary",
    "conversation_summary",
    "reply_draft",
    "lead_status_summary",
    "lead_next_action_suggestion",
    "campaign_performance_summary",
    "campaign_observation_suggestion",
    "feedback_theme_summary",
    "feedback_categorization",
    "root_cause_hypothesis",
    "product_performance_summary",
    "metric_change_explanation",
    "inventory_risk_summary",
    "knowledge_content_draft",
    "report_narrative",
    "management_review_questions",
    "dashboard_summary",
    "anomaly_evidence_summary",
    "nl_question_query_plan",
)
AI_PROVIDER_CODES = ("openai", "groq", "mock")
AI_REQUEST_STATUSES = ("pending", "completed", "failed", "blocked")
AI_FEEDBACK_OUTCOMES = ("accepted", "edited", "rejected", "ignored")


class AiRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The full audit record of one controlled-AI call —
    GROWTH_AND_INTELLIGENCE.md section 14.4. `estimated_cost_minor` follows
    the project's `_minor` integer-minor-unit money convention even though
    it tracks USD provider billing cost (not a restaurant business value in
    INR) — applying the same non-float rule everywhere avoids a second,
    inconsistent numeric-money precedent in the codebase.

    Never stores secrets/credentials (section 14.4's explicit rule) —
    `provider_code`/`model_reference` name the configuration, they never
    hold the API key itself.
    """

    __tablename__ = "ai_requests"
    __table_args__ = (
        CheckConstraint(f"feature_code IN {AI_FEATURE_CODES!r}", name="valid_feature_code"),
        CheckConstraint(f"provider_code IN {AI_PROVIDER_CODES!r}", name="valid_provider_code"),
        CheckConstraint(f"status IN {AI_REQUEST_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0", name="non_negative_input_tokens"
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0", name="non_negative_output_tokens"
        ),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="non_negative_latency"),
        Index("ix_ai_requests_requested_by_staff_id", "requested_by_staff_id", "created_at"),
        Index("ix_ai_requests_feature_code", "feature_code"),
        Index("ix_ai_requests_status", "status"),
    )

    requested_by_staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_users.id"), nullable=False
    )
    feature_code: Mapped[str] = mapped_column(String(48), nullable=False)
    prompt_template_code: Mapped[str] = mapped_column(String(48), nullable=False)
    prompt_template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_code: Mapped[str] = mapped_column(String(16), nullable=False)
    model_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    permission_scope: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    input_record_refs: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB, nullable=True)
    grounding_summary: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_structured: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    confidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    failure_category: Mapped[str | None] = mapped_column(String(48), nullable=True)
    safety_blocked: Mapped[bool] = mapped_column(nullable=False, default=False)
    safety_block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AiRequestFeedback(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Staff review of an AI output — section 14.6/14.8's "AI output is
    never silently written into final records" is enforced by requiring
    this explicit accept/edit/reject/ignore event before anything derived
    from `AiRequest.output_text` is copied elsewhere."""

    __tablename__ = "ai_request_feedback"
    __table_args__ = (
        CheckConstraint(f"outcome_state IN {AI_FEEDBACK_OUTCOMES!r}", name="valid_outcome_state"),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="valid_rating"),
        Index("ix_ai_request_feedback_ai_request_id", "ai_request_id"),
    )

    ai_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_requests.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    outcome_state: Mapped[str] = mapped_column(String(16), nullable=False)
    edited_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class AiSourceReference(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """A grounding citation retained for an `AiRequest` — section 14.5's
    "source record references must be retained" / "expose the relevant
    source timeline or records to the user." `source_id` is stored as text
    since sources vary in identifier shape (a record UUID, or a metric
    code string for a cited metric)."""

    __tablename__ = "ai_source_references"
    __table_args__ = (Index("ix_ai_source_references_ai_request_id", "ai_request_id"),)

    ai_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_requests.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    source_label: Mapped[str | None] = mapped_column(String(200), nullable=True)


class AiPromptTemplate(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Centrally managed, versioned prompt template — section 14.7. Only
    one version per `feature_code` may be `is_active` at a time (enforced
    by a partial unique index), so `app.controlled_ai.service` always has
    exactly one unambiguous active template to load per feature."""

    __tablename__ = "ai_prompt_templates"
    __table_args__ = (
        CheckConstraint(f"feature_code IN {AI_FEATURE_CODES!r}", name="valid_feature_code"),
        Index("uq_ai_prompt_templates_feature_version", "feature_code", "version", unique=True),
        Index(
            "uq_ai_prompt_templates_one_active_per_feature",
            "feature_code",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    feature_code: Mapped[str] = mapped_column(String(48), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_input_fields: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    prohibited_data: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    max_context_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_config_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
