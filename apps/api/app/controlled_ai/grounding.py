"""Evidence assembly — GROWTH_AND_INTELLIGENCE.md section 14.5's grounding
rules: "AI receives only data required for the task," "data access follows
backend permissions," "source record references must be retained." Every
function here returns `(user_prompt_text, grounding_summary, source_refs)`
— the model never sees anything beyond what's assembled here, and every
fact cited traces back to a `source_refs` entry recorded as an
`AiSourceReference` row.
"""

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.engine import MetricResult, run_metric_query
from app.analytics_core.registry import METRIC_CODES
from app.anomalies.service import get_finding as get_anomaly_finding
from app.controlled_ai.errors import ControlledAiError
from app.reports.service import get_dashboard, get_report_run, get_report_run_dataset

SourceRef = tuple[str, str, str | None]  # (source_type, source_id, label)


def _metric_result_summary(result: MetricResult) -> dict[str, object]:
    return {
        "metric_code": result.metric.code,
        "display_name": result.metric.display_name,
        "value": float(result.value),
        "comparison_value": float(result.comparison_value)
        if result.comparison_value is not None
        else None,
        "change_pct": float(result.change_pct) if result.change_pct is not None else None,
        "unit": result.metric.unit,
    }


async def ground_dashboard_summary(
    session: AsyncSession, *, permissions: frozenset[str], domain: str, window_code: str
) -> tuple[str, dict[str, object], list[SourceRef]]:
    _window, results, _skipped = await get_dashboard(
        session,
        domain=domain,
        permissions=permissions,
        window_code=window_code,
        custom_start=None,
        custom_end=None,
    )
    metrics = [_metric_result_summary(r) for r in results]
    grounding: dict[str, object] = {"domain": domain, "window": window_code, "metrics": metrics}
    source_refs: list[SourceRef] = [
        ("metric", r.metric.code, r.metric.display_name) for r in results
    ]
    return json.dumps(grounding, default=str), grounding, source_refs


async def ground_metric_change_explanation(
    session: AsyncSession, *, permissions: frozenset[str], metric_code: str, window_code: str
) -> tuple[str, dict[str, object], list[SourceRef]]:
    if metric_code not in METRIC_CODES:
        raise ControlledAiError(f"Unknown metric code: {metric_code!r}")
    result = await run_metric_query(
        session, metric_code=metric_code, permissions=permissions, window_code=window_code
    )
    grounding = _metric_result_summary(result)
    return (
        json.dumps(grounding, default=str),
        grounding,
        [("metric", metric_code, result.metric.display_name)],
    )


async def ground_anomaly_evidence_summary(
    session: AsyncSession, *, finding_id: uuid.UUID
) -> tuple[str, dict[str, object], list[SourceRef]]:
    finding = await get_anomaly_finding(session, finding_id)
    if finding is None:
        raise ControlledAiError("Anomaly finding not found.")
    grounding: dict[str, object] = {
        "metric_code": finding.metric_code,
        "observed_value": float(finding.observed_value) if finding.observed_value else None,
        "expected_value": float(finding.expected_value) if finding.expected_value else None,
        "deviation_pct": float(finding.deviation_pct) if finding.deviation_pct else None,
        "severity": finding.severity,
        "evidence": finding.evidence,
    }
    return (
        json.dumps(grounding, default=str),
        grounding,
        [("anomaly_finding", str(finding.id), finding.metric_code)],
    )


async def ground_report_narrative(
    session: AsyncSession, *, report_run_id: uuid.UUID
) -> tuple[str, dict[str, object], list[SourceRef]]:
    run = await get_report_run(session, report_run_id)
    if run is None:
        raise ControlledAiError("Report run not found.")
    dataset = await get_report_run_dataset(session, report_run_id)
    metrics = dataset.result_data.get("metrics", []) if dataset else []
    grounding = {
        "window_code": run.window_code,
        "window_start": run.window_start.isoformat(),
        "window_end": run.window_end.isoformat(),
        "metrics": metrics,
    }
    source_refs: list[SourceRef] = [("report_run", str(run.id), run.window_code)]
    if isinstance(metrics, list):
        source_refs.extend(
            ("metric", str(m.get("metric_code")), str(m.get("display_name")))
            for m in metrics
            if isinstance(m, dict)
        )
    return json.dumps(grounding, default=str), grounding, source_refs


async def ground_nl_question_query_plan(
    *, question: str, permissions: frozenset[str]
) -> tuple[str, dict[str, object], list[SourceRef]]:
    from app.analytics_core.registry import METRICS

    available = [m.code for m in METRICS if m.required_permission in permissions]
    grounding: dict[str, object] = {"question": question, "available_metric_codes": available}
    return json.dumps(grounding, default=str), grounding, []
