from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.windows import ResolvedWindow
from app.db.models import AttendanceRecord, StaffUser, TaskRecord


async def active_count(session: AsyncSession, window: ResolvedWindow) -> int:
    """Point-in-time gauge as of the window's end boundary."""
    value = await session.scalar(
        select(func.count()).select_from(StaffUser).where(StaffUser.account_status == "active")
    )
    return int(value or 0)


async def overdue_tasks(session: AsyncSession, window: ResolvedWindow) -> int:
    """Point-in-time gauge: tasks still open past their due date as of the
    window's end boundary — mirrors `open_high_severity_complaints`."""
    value = await session.scalar(
        select(func.count())
        .select_from(TaskRecord)
        .where(
            TaskRecord.status.not_in(("completed", "cancelled")),
            TaskRecord.due_at.is_not(None),
            TaskRecord.due_at < window.end,
        )
    )
    return int(value or 0)


async def attendance_rate_pct(session: AsyncSession, window: ResolvedWindow) -> Decimal:
    """Present-or-late attendance records as a share of all recorded
    attendance within the window (excluding scheduled-off days, which
    are not attendance outcomes)."""
    excluded = ("weekly_off", "holiday")
    recorded = await session.scalar(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.status.not_in(excluded),
            AttendanceRecord.created_at >= window.start,
            AttendanceRecord.created_at < window.end,
        )
    )
    if not recorded:
        return Decimal(0)
    present = await session.scalar(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.status.in_(("present", "late")),
            AttendanceRecord.created_at >= window.start,
            AttendanceRecord.created_at < window.end,
        )
    )
    return (Decimal(present or 0) / Decimal(recorded)) * Decimal(100)
