"""Centrally managed prompt templates — GROWTH_AND_INTELLIGENCE.md section
14.7. `PROMPT_TEMPLATES` is the code-defined source (the same
registry-then-seed-syncs-the-table pattern `app.permissions.registry`
already established); `app.db.seed` upserts one active `AiPromptTemplate`
row per entry here.

Scope: this phase wires grounding and a working service path for five
capabilities — the ones that are Phase 14's own domain (dashboards,
metrics, anomalies, reports, and a natural-language query planner). The
other capability codes already exist in `AI_FEATURE_CODES`
(`app.db.models.ai_request`) for future phases to wire their own grounding
against; they intentionally have no template here yet, so they cannot be
requested until they do (`app.controlled_ai.service` rejects an unknown-
template feature code rather than running ungrounded).
"""

from dataclasses import dataclass

_SHARED_SAFETY_CONSTRAINTS = (
    "Advisory only. Never claim a fact not present in the supplied evidence. "
    "Never propose or imply a mutating action. State when data is missing or "
    "uncertain. Distinguish correlation from causation. Cite the metric codes, "
    "periods, and record references the evidence provides."
)


@dataclass(frozen=True)
class PromptTemplateDef:
    feature_code: str
    version: int
    purpose: str
    allowed_input_fields: tuple[str, ...]
    prohibited_data: tuple[str, ...]
    output_schema: dict[str, object] | None
    max_context_tokens: int
    safety_constraints: str
    model_config_reference: str
    system_prompt: str


PROMPT_TEMPLATES: tuple[PromptTemplateDef, ...] = (
    PromptTemplateDef(
        feature_code="dashboard_summary",
        version=1,
        purpose="Summarize a domain dashboard's current metrics in plain language.",
        allowed_input_fields=("domain", "window", "metrics"),
        prohibited_data=("staff_pii", "customer_pii", "secrets"),
        output_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "highlights": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "highlights"],
        },
        max_context_tokens=4000,
        safety_constraints=_SHARED_SAFETY_CONSTRAINTS,
        model_config_reference="default",
        system_prompt=(
            "You summarize restaurant operational dashboard metrics for a manager. "
            "Use only the structured metric evidence you are given. " + _SHARED_SAFETY_CONSTRAINTS
        ),
    ),
    PromptTemplateDef(
        feature_code="metric_change_explanation",
        version=1,
        purpose="Explain why a single metric changed versus its comparison period.",
        allowed_input_fields=("metric_code", "value", "comparison_value", "change_pct", "window"),
        prohibited_data=("staff_pii", "customer_pii", "secrets"),
        output_schema={
            "type": "object",
            "properties": {
                "explanation": {"type": "string"},
                "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["explanation", "confidence"],
        },
        max_context_tokens=2000,
        safety_constraints=_SHARED_SAFETY_CONSTRAINTS,
        model_config_reference="default",
        system_prompt=(
            "You explain a single metric's period-over-period change using only the "
            "supplied numbers. Never claim a specific cause the data does not "
            "support; describe the change and note plausible, clearly-labelled "
            "hypotheses only when evidence-supported. " + _SHARED_SAFETY_CONSTRAINTS
        ),
    ),
    PromptTemplateDef(
        feature_code="anomaly_evidence_summary",
        version=1,
        purpose="Summarize a detected anomaly's evidence for staff review.",
        allowed_input_fields=("metric_code", "observed_value", "expected_value", "evidence"),
        prohibited_data=("staff_pii", "customer_pii", "secrets"),
        output_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "suggested_next_step": {"type": "string"},
            },
            "required": ["summary", "suggested_next_step"],
        },
        max_context_tokens=2000,
        safety_constraints=_SHARED_SAFETY_CONSTRAINTS,
        model_config_reference="default",
        system_prompt=(
            "You summarize a deterministic anomaly-detection finding for a manager "
            "reviewing it. Describe what was observed and why the rule flagged it, "
            "using only the supplied evidence. Suggest one concrete next step a "
            "manager could take, never an automated action. " + _SHARED_SAFETY_CONSTRAINTS
        ),
    ),
    PromptTemplateDef(
        feature_code="report_narrative",
        version=1,
        purpose="Draft a short narrative summary of a completed report run.",
        allowed_input_fields=("report_name", "window", "metrics"),
        prohibited_data=("staff_pii", "customer_pii", "secrets"),
        output_schema={
            "type": "object",
            "properties": {
                "narrative": {"type": "string"},
            },
            "required": ["narrative"],
        },
        max_context_tokens=4000,
        safety_constraints=_SHARED_SAFETY_CONSTRAINTS,
        model_config_reference="default",
        system_prompt=(
            "You draft a short narrative summary for a business report, for a "
            "manager to review and edit before it becomes part of the report. "
            "Use only the supplied metric evidence. " + _SHARED_SAFETY_CONSTRAINTS
        ),
    ),
    PromptTemplateDef(
        feature_code="nl_question_query_plan",
        version=1,
        purpose=(
            "Translate a natural-language analytics question into an allowlisted "
            "structured query plan (metric code + window) — never SQL, never "
            "executed by the model itself."
        ),
        allowed_input_fields=("question", "available_metric_codes"),
        prohibited_data=("staff_pii", "customer_pii", "secrets", "raw_sql"),
        output_schema={
            "type": "object",
            "properties": {
                "metric_code": {"type": "string"},
                "window_code": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": ["metric_code", "window_code", "rationale"],
        },
        max_context_tokens=2000,
        safety_constraints=(
            "You propose a query PLAN only — a metric_code from the allowlisted set "
            "you are given, plus a window_code. You never write or execute SQL, and "
            "your proposed metric_code is validated by the server against the real "
            "metric registry before anything runs. " + _SHARED_SAFETY_CONSTRAINTS
        ),
        model_config_reference="default",
        system_prompt=(
            "You translate a manager's natural-language analytics question into a "
            "structured query plan using only the metric codes you are given. "
            "Never invent a metric code."
        ),
    ),
)

_TEMPLATES_BY_FEATURE: dict[str, PromptTemplateDef] = {t.feature_code: t for t in PROMPT_TEMPLATES}


def get_prompt_template(feature_code: str) -> PromptTemplateDef | None:
    return _TEMPLATES_BY_FEATURE.get(feature_code)
