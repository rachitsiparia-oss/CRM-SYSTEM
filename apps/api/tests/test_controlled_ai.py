"""Tests for `app.controlled_ai` — the mock provider path (always active
in this test environment, since no live AI credentials are configured),
structured-output validation against each capability's real schema, and
unsupported-feature rejection. GROWTH_AND_INTELLIGENCE.md section 14.13:
"all features are advisory," "structured outputs are validated.\""""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from app.controlled_ai import service as ai_service
from app.controlled_ai.errors import UnsupportedFeatureError
from app.controlled_ai.providers import MockAiProvider
from app.controlled_ai.safety import validate_structured_output
from app.db.models import StaffUser
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]

_DASHBOARD_PERMISSIONS = frozenset({"ai.analytics.use", "analytics.executive.view"})


@pytest.fixture(autouse=True)
def _force_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """This environment's local `.env` may carry a placeholder
    `OPENAI_API_KEY`, which would otherwise route these tests through a
    real (failing) network call — force the deterministic mock provider
    so these tests exercise the pipeline, not the local machine's env."""
    monkeypatch.setattr(ai_service, "get_ai_provider", lambda *a, **k: MockAiProvider())


def test_validate_structured_output_requires_declared_fields() -> None:
    schema: dict[str, object] = {"type": "object", "required": ["summary", "highlights"]}
    assert validate_structured_output(schema, {"summary": "x", "highlights": []})
    assert not validate_structured_output(schema, {"summary": "x"})
    assert not validate_structured_output(schema, None)
    assert validate_structured_output(None, None)


async def test_request_completion_unknown_feature_raises(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    with pytest.raises(UnsupportedFeatureError):
        await ai_service.request_completion(
            db_session,
            actor=actor,
            feature_code="reply_draft",  # a real AI_FEATURE_CODES value with no template yet
            permissions=_DASHBOARD_PERMISSIONS,
            params={},
        )


async def test_request_completion_dashboard_summary_completes_with_grounding(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    ai_request = await ai_service.request_completion(
        db_session,
        actor=actor,
        feature_code="dashboard_summary",
        permissions=_DASHBOARD_PERMISSIONS,
        params={"domain": "executive", "window_code": "current_month"},
    )
    assert ai_request.status == "completed"
    assert ai_request.provider_code == "mock"
    assert ai_request.output_structured is not None
    assert "summary" in ai_request.output_structured
    assert "highlights" in ai_request.output_structured
    assert ai_request.grounding_summary is not None
    assert ai_request.input_record_refs


async def test_request_completion_metric_change_explanation_grounds_single_metric(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    ai_request = await ai_service.request_completion(
        db_session,
        actor=actor,
        feature_code="metric_change_explanation",
        permissions=_DASHBOARD_PERMISSIONS,
        params={"metric_code": "exec_net_sales", "window_code": "current_month"},
    )
    assert ai_request.status == "completed"
    assert ai_request.output_structured is not None
    assert "explanation" in ai_request.output_structured
    assert "confidence" in ai_request.output_structured


async def test_request_completion_report_narrative_missing_run_fails_gracefully(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    import uuid

    actor = await make_staff_user()
    from app.controlled_ai.errors import ControlledAiError

    with pytest.raises(ControlledAiError):
        await ai_service.request_completion(
            db_session,
            actor=actor,
            feature_code="report_narrative",
            permissions=_DASHBOARD_PERMISSIONS,
            params={"report_run_id": str(uuid.uuid4())},
        )


async def test_ground_nl_question_query_plan_rejects_oversized_question() -> None:
    from app.controlled_ai import grounding
    from app.controlled_ai.errors import ControlledAiError

    oversized = "x" * (grounding._MAX_QUESTION_LENGTH + 1)
    with pytest.raises(ControlledAiError):
        await grounding.ground_nl_question_query_plan(
            question=oversized, permissions=_DASHBOARD_PERMISSIONS
        )


async def test_request_completion_rejects_oversized_question(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    from app.controlled_ai import grounding
    from app.controlled_ai.errors import ControlledAiError

    actor = await make_staff_user()
    oversized = "x" * (grounding._MAX_QUESTION_LENGTH + 1)
    with pytest.raises(ControlledAiError):
        await ai_service.request_completion(
            db_session,
            actor=actor,
            feature_code="nl_question_query_plan",
            permissions=_DASHBOARD_PERMISSIONS,
            params={"question": oversized},
        )


async def test_hr_sensitive_block_is_recorded_on_the_request_row(
    db_session: AsyncSession,
    make_staff_user: MakeStaffUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # HR_SENSITIVE_FEATURE_CODES is empty today (no wired capability touches
    # HR data yet) — force the check to fire for dashboard_summary so the
    # blocked-request audit trail can be exercised end to end.
    monkeypatch.setattr(ai_service, "requires_hr_sensitive_permission", lambda code: True)
    actor = await make_staff_user()
    ai_request = await ai_service.request_completion(
        db_session,
        actor=actor,
        feature_code="dashboard_summary",
        permissions=_DASHBOARD_PERMISSIONS,  # lacks ai.analytics.hr_sensitive
        params={"domain": "executive", "window_code": "current_month"},
    )
    assert ai_request.status == "blocked"
    assert ai_request.safety_blocked is True
    assert ai_request.safety_block_reason is not None
    assert ai_request.completed_at is not None
    # No grounding/provider call happened — the request never left the
    # blocked state to reach either.
    assert ai_request.output_text is None


async def test_record_feedback_persists_outcome(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    from app.controlled_ai.schemas import AiRequestFeedbackIn

    actor = await make_staff_user()
    ai_request = await ai_service.request_completion(
        db_session,
        actor=actor,
        feature_code="dashboard_summary",
        permissions=_DASHBOARD_PERMISSIONS,
        params={"domain": "executive", "window_code": "current_month"},
    )
    feedback = await ai_service.record_feedback(
        db_session,
        actor=actor,
        ai_request=ai_request,
        payload=AiRequestFeedbackIn(outcome_state="accepted", rating=5),
    )
    assert feedback.outcome_state == "accepted"
    assert feedback.rating == 5
    assert feedback.staff_id == actor.id
