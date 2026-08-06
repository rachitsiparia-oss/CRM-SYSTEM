"""Controlled AI request orchestration — GROWTH_AND_INTELLIGENCE.md section
14. Every request is fully audited (`AiRequest`), grounded with retained
source references (`AiSourceReference`), and schema-validated before its
structured output is trusted. A provider failure or validation failure
never raises past this layer as an unhandled error and never mutates any
business record — it is recorded on the `AiRequest` row itself as a
`status="failed"`/`"blocked"` outcome the caller renders gracefully
(section 14.9's "AI outage does not block core CRM").
"""

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.controlled_ai import grounding
from app.controlled_ai.errors import ControlledAiError, UnsupportedFeatureError
from app.controlled_ai.prompts import get_prompt_template
from app.controlled_ai.providers import get_ai_provider
from app.controlled_ai.safety import requires_hr_sensitive_permission, validate_structured_output
from app.db.models import AiRequest, AiRequestFeedback, AiSourceReference, StaffUser


async def request_completion(
    session: AsyncSession,
    *,
    actor: StaffUser,
    feature_code: str,
    permissions: frozenset[str],
    params: dict[str, object],
) -> AiRequest:
    template = get_prompt_template(feature_code)
    if template is None:
        raise UnsupportedFeatureError(
            f"No active prompt template for feature {feature_code!r} — this capability "
            "is not yet wired in this phase."
        )

    ai_request = AiRequest(
        requested_by_staff_id=actor.id,
        feature_code=feature_code,
        prompt_template_code=feature_code,
        prompt_template_version=template.version,
        provider_code="mock",
        model_reference="unresolved",
        permission_scope=sorted(permissions),
        status="pending",
    )
    session.add(ai_request)
    await session.flush()

    if requires_hr_sensitive_permission(feature_code) and "ai.analytics.hr_sensitive" not in (
        permissions
    ):
        # Recorded on the request itself, not just raised, so a blocked
        # attempt at HR-sensitive AI access leaves the same audit trail
        # every other outcome does (CLAUDE.md section 6.6's "AI actions
        # that affect business records" — a blocked attempt is itself a
        # security-relevant event worth a durable record).
        ai_request.status = "blocked"
        ai_request.safety_blocked = True
        ai_request.safety_block_reason = "Requires ai.analytics.hr_sensitive permission."
        ai_request.completed_at = datetime.now(UTC)
        await session.flush()
        return ai_request

    try:
        user_prompt, grounding_summary, source_refs = await _assemble_grounding(
            session, feature_code=feature_code, permissions=permissions, params=params
        )
    except ControlledAiError as exc:
        ai_request.status = "failed"
        ai_request.failure_category = "grounding_error"
        ai_request.completed_at = datetime.now(UTC)
        await session.flush()
        raise exc

    ai_request.grounding_summary = grounding_summary
    ai_request.input_record_refs = [
        {"source_type": t, "source_id": i, "label": lbl} for t, i, lbl in source_refs
    ]

    provider = get_ai_provider()
    started = time.monotonic()
    result = await provider.complete(
        system_prompt=template.system_prompt,
        user_prompt=user_prompt,
        response_schema=template.output_schema,
    )
    latency_ms = result.latency_ms or int((time.monotonic() - started) * 1000)

    ai_request.provider_code = (
        result.provider_code
        if result.provider_code
        in (
            "openai",
            "groq",
            "mock",
        )
        else "mock"
    )
    ai_request.model_reference = result.model_reference
    ai_request.latency_ms = latency_ms
    ai_request.input_tokens = result.input_tokens
    ai_request.output_tokens = result.output_tokens

    if not result.accepted:
        ai_request.status = "failed"
        ai_request.failure_category = result.failure_reason or "provider_error"
        ai_request.completed_at = datetime.now(UTC)
        await session.flush()
        return ai_request

    if not validate_structured_output(template.output_schema, result.output_structured):
        ai_request.status = "failed"
        ai_request.failure_category = "invalid_structured_output"
        ai_request.output_text = result.output_text
        ai_request.completed_at = datetime.now(UTC)
        await session.flush()
        return ai_request

    ai_request.status = "completed"
    ai_request.output_text = result.output_text
    ai_request.output_structured = result.output_structured
    ai_request.completed_at = datetime.now(UTC)
    await session.flush()

    for source_type, source_id, label in source_refs:
        session.add(
            AiSourceReference(
                ai_request_id=ai_request.id,
                source_type=source_type,
                source_id=source_id,
                source_label=label,
            )
        )
    await session.flush()
    return ai_request


async def _assemble_grounding(
    session: AsyncSession,
    *,
    feature_code: str,
    permissions: frozenset[str],
    params: dict[str, object],
) -> tuple[str, dict[str, object], list[grounding.SourceRef]]:
    if feature_code == "dashboard_summary":
        return await grounding.ground_dashboard_summary(
            session,
            permissions=permissions,
            domain=str(params["domain"]),
            window_code=str(params.get("window_code", "current_month")),
        )
    if feature_code == "metric_change_explanation":
        return await grounding.ground_metric_change_explanation(
            session,
            permissions=permissions,
            metric_code=str(params["metric_code"]),
            window_code=str(params.get("window_code", "current_month")),
        )
    if feature_code == "anomaly_evidence_summary":
        return await grounding.ground_anomaly_evidence_summary(
            session, finding_id=uuid.UUID(str(params["finding_id"]))
        )
    if feature_code == "report_narrative":
        return await grounding.ground_report_narrative(
            session, report_run_id=uuid.UUID(str(params["report_run_id"]))
        )
    if feature_code == "nl_question_query_plan":
        return await grounding.ground_nl_question_query_plan(
            question=str(params["question"]), permissions=permissions
        )
    raise ControlledAiError(f"No grounding assembler registered for {feature_code!r}.")


async def get_ai_request(session: AsyncSession, request_id: uuid.UUID) -> AiRequest | None:
    return await session.get(AiRequest, request_id)


async def record_feedback(
    session: AsyncSession, *, actor: StaffUser, ai_request: AiRequest, payload: object
) -> AiRequestFeedback:
    from app.controlled_ai.schemas import AiRequestFeedbackIn

    assert isinstance(payload, AiRequestFeedbackIn)
    feedback = AiRequestFeedback(
        ai_request_id=ai_request.id,
        staff_id=actor.id,
        outcome_state=payload.outcome_state,
        edited_content=payload.edited_content,
        rating=payload.rating,
        feedback_note=payload.feedback_note,
    )
    session.add(feedback)
    await session.flush()
    return feedback
