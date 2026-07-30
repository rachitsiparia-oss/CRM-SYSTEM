"""Attendance recording and corrections — this phase's own instruction
section 19. Corrections are never silent overwrites: every correction
creates an immutable `AttendanceCorrection` row snapshotting before/after
values alongside updating the current-state `AttendanceRecord` row.
"""

import uuid
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AttendanceCorrection, AttendanceRecord, StaffShift, StaffUser
from app.staff_operations.schemas import AttendanceCorrectionIn, AttendanceRecordCreateIn


def _compute_minutes(
    *,
    scheduled_start: datetime | None,
    scheduled_end: datetime | None,
    actual_in: datetime | None,
    actual_out: datetime | None,
) -> tuple[int, int, int]:
    late_minutes = 0
    early_leave_minutes = 0
    worked_minutes = 0
    if scheduled_start and actual_in and actual_in > scheduled_start:
        late_minutes = int((actual_in - scheduled_start).total_seconds() // 60)
    if scheduled_end and actual_out and actual_out < scheduled_end:
        early_leave_minutes = int((scheduled_end - actual_out).total_seconds() // 60)
    if actual_in and actual_out and actual_out > actual_in:
        worked_minutes = int((actual_out - actual_in).total_seconds() // 60)
    return late_minutes, early_leave_minutes, worked_minutes


async def record_attendance(
    session: AsyncSession, *, actor: StaffUser, payload: AttendanceRecordCreateIn
) -> AttendanceRecord:
    if (
        payload.actual_check_out_at
        and payload.actual_check_in_at
        and (payload.actual_check_out_at < payload.actual_check_in_at)
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Check-out cannot be before check-in."
        )
    existing = await session.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.staff_user_id == payload.staff_user_id,
            AttendanceRecord.attendance_date == payload.attendance_date,
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="An attendance record already exists for this date."
        )
    scheduled_start = scheduled_end = None
    if payload.shift_id is not None:
        shift = await session.get(StaffShift, payload.shift_id)
        if shift is not None:
            scheduled_start, scheduled_end = shift.start_at, shift.end_at
    late, early, worked = _compute_minutes(
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        actual_in=payload.actual_check_in_at,
        actual_out=payload.actual_check_out_at,
    )
    record = AttendanceRecord(
        staff_user_id=payload.staff_user_id,
        attendance_date=payload.attendance_date,
        shift_id=payload.shift_id,
        scheduled_start_at=scheduled_start,
        scheduled_end_at=scheduled_end,
        actual_check_in_at=payload.actual_check_in_at,
        actual_check_out_at=payload.actual_check_out_at,
        status=payload.status,
        late_minutes=late,
        early_leave_minutes=early,
        worked_minutes=worked,
        created_by=actor.id,
    )
    session.add(record)
    await session.flush()
    return record


async def correct_attendance(
    session: AsyncSession,
    *,
    actor: StaffUser,
    record: AttendanceRecord,
    payload: AttendanceCorrectionIn,
) -> AttendanceRecord:
    previous_values = {
        "status": record.status,
        "actual_check_in_at": record.actual_check_in_at.isoformat()
        if record.actual_check_in_at
        else None,
        "actual_check_out_at": record.actual_check_out_at.isoformat()
        if record.actual_check_out_at
        else None,
    }
    new_check_in = payload.actual_check_in_at or record.actual_check_in_at
    new_check_out = payload.actual_check_out_at or record.actual_check_out_at
    if new_check_in and new_check_out and new_check_out < new_check_in:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Check-out cannot be before check-in."
        )
    if payload.status is not None:
        record.status = payload.status
    if payload.actual_check_in_at is not None:
        record.actual_check_in_at = payload.actual_check_in_at
    if payload.actual_check_out_at is not None:
        record.actual_check_out_at = payload.actual_check_out_at
    late, early, worked = _compute_minutes(
        scheduled_start=record.scheduled_start_at,
        scheduled_end=record.scheduled_end_at,
        actual_in=record.actual_check_in_at,
        actual_out=record.actual_check_out_at,
    )
    record.late_minutes = late
    record.early_leave_minutes = early
    record.worked_minutes = worked
    record.is_corrected = True
    record.correction_reason = payload.reason
    record.corrected_by = actor.id
    new_values = {
        "status": record.status,
        "actual_check_in_at": record.actual_check_in_at.isoformat()
        if record.actual_check_in_at
        else None,
        "actual_check_out_at": record.actual_check_out_at.isoformat()
        if record.actual_check_out_at
        else None,
    }
    session.add(
        AttendanceCorrection(
            attendance_record_id=record.id,
            previous_values=previous_values,
            new_values=new_values,
            reason=payload.reason,
            corrected_by=actor.id,
            approval_state="approved",
        )
    )
    await session.flush()
    return record


async def list_attendance(
    session: AsyncSession,
    *,
    staff_user_id: uuid.UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> list[AttendanceRecord]:
    stmt = select(AttendanceRecord)
    if staff_user_id:
        stmt = stmt.where(AttendanceRecord.staff_user_id == staff_user_id)
    if start_date:
        stmt = stmt.where(AttendanceRecord.attendance_date >= start_date)
    if end_date:
        stmt = stmt.where(AttendanceRecord.attendance_date <= end_date)
    stmt = stmt.order_by(AttendanceRecord.attendance_date.desc())
    return list((await session.scalars(stmt)).all())
