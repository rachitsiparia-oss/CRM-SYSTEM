"""Deterministic, bounded service-recovery analytics — instruction section
20 (not Phase 14's full reporting platform)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ServiceRecoveryAction
from app.service_recovery.schemas import RecoveryAnalyticsOut


async def get_analytics(session: AsyncSession) -> RecoveryAnalyticsOut:
    since = datetime.now(UTC) - timedelta(days=30)

    by_type_rows = (
        await session.execute(
            select(ServiceRecoveryAction.recovery_type, func.count())
            .where(ServiceRecoveryAction.created_at >= since)
            .group_by(ServiceRecoveryAction.recovery_type)
        )
    ).all()
    by_status_rows = (
        await session.execute(
            select(ServiceRecoveryAction.status, func.count())
            .where(ServiceRecoveryAction.created_at >= since)
            .group_by(ServiceRecoveryAction.status)
        )
    ).all()

    total_value = await session.scalar(
        select(func.coalesce(func.sum(ServiceRecoveryAction.value_minor), 0)).where(
            ServiceRecoveryAction.created_at >= since,
            ServiceRecoveryAction.status == "completed",
        )
    )
    total_points = await session.scalar(
        select(func.coalesce(func.sum(ServiceRecoveryAction.points), 0)).where(
            ServiceRecoveryAction.created_at >= since,
            ServiceRecoveryAction.status == "completed",
        )
    )
    approved_count = await session.scalar(
        select(func.count())
        .select_from(ServiceRecoveryAction)
        .where(
            ServiceRecoveryAction.created_at >= since,
            ServiceRecoveryAction.approved_at.is_not(None),
        )
    )
    rejected_count = await session.scalar(
        select(func.count())
        .select_from(ServiceRecoveryAction)
        .where(
            ServiceRecoveryAction.created_at >= since, ServiceRecoveryAction.status == "rejected"
        )
    )
    proposed_total = await session.scalar(
        select(func.count())
        .select_from(ServiceRecoveryAction)
        .where(ServiceRecoveryAction.created_at >= since)
    )
    completed_total = await session.scalar(
        select(func.count())
        .select_from(ServiceRecoveryAction)
        .where(
            ServiceRecoveryAction.created_at >= since, ServiceRecoveryAction.status == "completed"
        )
    )

    proposed_total = proposed_total or 0
    completed_total = completed_total or 0
    completion_rate = completed_total / proposed_total * 100 if proposed_total else 0.0

    return RecoveryAnalyticsOut(
        by_type=[{"recovery_type": row[0], "count": row[1]} for row in by_type_rows],
        by_status=[{"status": row[0], "count": row[1]} for row in by_status_rows],
        total_value_minor_30d=int(total_value or 0),
        total_points_30d=int(total_points or 0),
        approved_count_30d=int(approved_count or 0),
        rejected_count_30d=int(rejected_count or 0),
        completion_rate_pct=round(completion_rate, 1),
    )
