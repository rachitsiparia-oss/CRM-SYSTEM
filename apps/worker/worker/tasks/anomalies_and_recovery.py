"""Anomaly evaluation, review-request scheduling, and complaint SLA
escalation — three engine functions that already existed (Phase 13/14) as
callables invoked only from an authenticated router action, never from a
scheduler. Each function's own docstring anticipates exactly this."""

from typing import Any

from app.anomalies.engine import evaluate_all_active_rules
from app.complaints.service import run_sla_escalations
from app.feedback.review_requests import process_pending_review_requests
from sqlalchemy.ext.asyncio import AsyncSession

from worker.scheduling import run_scheduled_job


async def evaluate_anomalies(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        findings = await evaluate_all_active_rules(session)
        return {"findings_created": len(findings)}

    return await run_scheduled_job(
        job_type="anomalies.evaluate_all_active",
        queue_name="reports",
        func=_run,
        max_attempts=3,
        timeout_seconds=300,
    )


async def process_review_requests(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        processed = await process_pending_review_requests(session)
        return {"processed": len(processed)}

    return await run_scheduled_job(
        job_type="feedback.process_review_requests",
        queue_name="communications",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )


async def run_complaint_sla_escalations(ctx: dict[str, Any]) -> dict[str, Any]:
    async def _run(session: AsyncSession) -> dict[str, Any]:
        escalations = await run_sla_escalations(session)
        return {"escalations": len(escalations)}

    return await run_scheduled_job(
        job_type="complaints.run_sla_escalations",
        queue_name="critical-domain",
        func=_run,
        max_attempts=3,
        timeout_seconds=180,
    )
