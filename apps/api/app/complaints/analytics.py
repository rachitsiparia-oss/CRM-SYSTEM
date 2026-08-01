"""Deterministic, bounded complaint/SLA analytics — instruction section 20's
"Complaint volume, resolution time, escalation rate... deterministic,
bounded, computed from real data" (not Phase 14's full reporting platform).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.complaints.schemas import ComplaintAnalyticsOut
from app.db.models import Complaint, ComplaintEscalation, ComplaintSlaEvent

_OPEN_STATUSES = (
    "new",
    "acknowledged",
    "investigating",
    "awaiting_customer",
    "awaiting_internal",
    "resolution_proposed",
    "reopened",
)


async def get_analytics(session: AsyncSession) -> ComplaintAnalyticsOut:
    since = datetime.now(UTC) - timedelta(days=30)

    open_count = await session.scalar(
        select(func.count()).select_from(Complaint).where(Complaint.status.in_(_OPEN_STATUSES))
    )
    new_30d = await session.scalar(
        select(func.count()).select_from(Complaint).where(Complaint.created_at >= since)
    )
    resolved_30d = await session.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.resolved_at.is_not(None), Complaint.resolved_at >= since)
    )
    reopened_30d = await session.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.reopened_at.is_not(None), Complaint.reopened_at >= since)
    )

    by_severity_rows = (
        await session.execute(
            select(Complaint.severity, func.count())
            .where(Complaint.created_at >= since)
            .group_by(Complaint.severity)
        )
    ).all()
    by_category_rows = (
        await session.execute(
            select(Complaint.category, func.count())
            .where(Complaint.created_at >= since)
            .group_by(Complaint.category)
        )
    ).all()

    avg_first_response_seconds = await session.scalar(
        select(
            func.avg(func.extract("epoch", Complaint.first_responded_at - Complaint.created_at))
        ).where(Complaint.first_responded_at.is_not(None), Complaint.created_at >= since)
    )
    avg_resolution_seconds = await session.scalar(
        select(func.avg(func.extract("epoch", Complaint.resolved_at - Complaint.created_at))).where(
            Complaint.resolved_at.is_not(None), Complaint.created_at >= since
        )
    )

    sla_eligible = await session.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.created_at >= since, Complaint.sla_policy_id.is_not(None))
    )
    sla_breached = await session.scalar(
        select(func.count(func.distinct(ComplaintSlaEvent.complaint_id)))
        .select_from(ComplaintSlaEvent)
        .join(Complaint, Complaint.id == ComplaintSlaEvent.complaint_id)
        .where(
            ComplaintSlaEvent.event_type.like("breached_%"),
            Complaint.created_at >= since,
        )
    )
    escalated_30d = await session.scalar(
        select(func.count(func.distinct(ComplaintEscalation.complaint_id)))
        .select_from(ComplaintEscalation)
        .where(ComplaintEscalation.created_at >= since)
    )

    sla_eligible = sla_eligible or 0
    new_30d = new_30d or 0
    sla_breach_rate = (sla_breached or 0) / sla_eligible * 100 if sla_eligible else 0.0
    escalation_rate = (escalated_30d or 0) / new_30d * 100 if new_30d else 0.0

    return ComplaintAnalyticsOut(
        open_count=int(open_count or 0),
        new_30d=new_30d,
        resolved_30d=int(resolved_30d or 0),
        reopened_30d=int(reopened_30d or 0),
        by_severity=[{"severity": row[0], "count": row[1]} for row in by_severity_rows],
        by_category=[{"category": row[0], "count": row[1]} for row in by_category_rows],
        average_first_response_minutes=(
            round(avg_first_response_seconds / 60, 1)
            if avg_first_response_seconds is not None
            else None
        ),
        average_resolution_minutes=(
            round(avg_resolution_seconds / 60, 1) if avg_resolution_seconds is not None else None
        ),
        sla_breach_rate_pct=round(sla_breach_rate, 1),
        escalation_rate_pct=round(escalation_rate, 1),
    )
