"""Staff dashboard analytics — this phase's own instruction section 29,
with exact calculation definitions recorded here and in
`docs/DATABASE_AND_API.md` section 12.6 (analytics definitions). All
counts are database-side aggregates over a single "today" boundary
computed once in `Asia/Kolkata` (CLAUDE.md section 7's configured
restaurant timezone), avoiding double counting across a UTC/local split.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AttendanceRecord,
    KnowledgeAcknowledgement,
    LeaveRequest,
    PerformanceReview,
    ShiftChangeRequest,
    StaffCertification,
    StaffDocument,
    StaffEmploymentProfile,
    StaffShift,
    StaffUser,
    TrainingAssignment,
)

_RESTAURANT_TZ = ZoneInfo("Asia/Kolkata")


def _today_local() -> date:
    return datetime.now(_RESTAURANT_TZ).date()


async def get_staff_analytics(session: AsyncSession) -> dict[str, object]:
    today = _today_local()
    now = datetime.now(UTC)

    active_staff = await session.scalar(
        select(func.count())
        .select_from(StaffUser)
        .where(StaffUser.account_status == "active", StaffUser.deleted_at.is_(None))
    )
    dept_rows = (
        await session.execute(
            select(StaffUser.department_id, func.count())
            .where(StaffUser.account_status == "active", StaffUser.deleted_at.is_(None))
            .group_by(StaffUser.department_id)
        )
    ).all()
    onboarding_in_progress = await session.scalar(
        select(func.count())
        .select_from(StaffEmploymentProfile)
        .where(StaffEmploymentProfile.lifecycle_status == "onboarding")
    )
    documents_expiring = await session.scalar(
        select(func.count())
        .select_from(StaffDocument)
        .where(
            StaffDocument.expiry_date.is_not(None),
            StaffDocument.expiry_date <= today + timedelta(days=30),
            StaffDocument.deleted_at.is_(None),
        )
    )
    certifications_expiring = await session.scalar(
        select(func.count())
        .select_from(StaffCertification)
        .where(
            StaffCertification.expiry_date.is_not(None),
            StaffCertification.expiry_date <= today + timedelta(days=30),
        )
    )
    on_leave_today = await session.scalar(
        select(func.count())
        .select_from(LeaveRequest)
        .where(
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today,
        )
    )
    scheduled_today = await session.scalar(
        select(func.count())
        .select_from(StaffShift)
        .where(StaffShift.shift_date == today, StaffShift.status != "cancelled")
    )
    attendance_exceptions = await session.scalar(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.attendance_date == today,
            AttendanceRecord.status.in_(("absent", "late", "missed_punch")),
        )
    )
    late_arrivals = await session.scalar(
        select(func.count())
        .select_from(AttendanceRecord)
        .where(AttendanceRecord.attendance_date == today, AttendanceRecord.late_minutes > 0)
    )
    training_overdue = await session.scalar(
        select(func.count())
        .select_from(TrainingAssignment)
        .where(
            TrainingAssignment.due_at.is_not(None),
            TrainingAssignment.due_at < now,
            TrainingAssignment.status.in_(("assigned", "in_progress")),
        )
    )
    total_mandatory = await session.scalar(select(func.count()).select_from(TrainingAssignment))
    completed_mandatory = await session.scalar(
        select(func.count())
        .select_from(TrainingAssignment)
        .where(TrainingAssignment.status == "completed")
    )
    mandatory_training_pct = (
        ((completed_mandatory or 0) / total_mandatory * 100) if total_mandatory else 0.0
    )
    total_acks = await session.scalar(select(func.count()).select_from(KnowledgeAcknowledgement))
    completed_acks = await session.scalar(
        select(func.count())
        .select_from(KnowledgeAcknowledgement)
        .where(KnowledgeAcknowledgement.acknowledged_at.is_not(None))
    )
    ack_completion_pct = ((completed_acks or 0) / total_acks * 100) if total_acks else 0.0
    reviews_due = await session.scalar(
        select(func.count())
        .select_from(PerformanceReview)
        .where(PerformanceReview.status.in_(("draft", "in_progress")))
    )
    open_shift_changes = await session.scalar(
        select(func.count())
        .select_from(ShiftChangeRequest)
        .where(ShiftChangeRequest.status == "pending")
    )

    return {
        "active_staff": active_staff or 0,
        "staff_by_department": [
            {"department_id": str(row[0]) if row[0] else None, "count": row[1]} for row in dept_rows
        ],
        "onboarding_in_progress": onboarding_in_progress or 0,
        "documents_expiring_30d": documents_expiring or 0,
        "certifications_expiring_30d": certifications_expiring or 0,
        "on_leave_today": on_leave_today or 0,
        "scheduled_today": scheduled_today or 0,
        "attendance_exceptions_today": attendance_exceptions or 0,
        "late_arrivals_today": late_arrivals or 0,
        "training_overdue": training_overdue or 0,
        "mandatory_training_completion_pct": round(mandatory_training_pct, 1),
        "knowledge_acknowledgement_completion_pct": round(ack_completion_pct, 1),
        "reviews_due": reviews_due or 0,
        "open_shift_change_requests": open_shift_changes or 0,
    }
