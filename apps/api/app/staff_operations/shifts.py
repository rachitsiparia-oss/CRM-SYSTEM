"""Shift templates, roster assignment, and shift-change requests — this
phase's own instruction section 17-18. Overlap detection compares full
`start_at`/`end_at` timestamp ranges (not time-of-day), which handles
overnight shifts correctly without special-casing midnight wraparound.
"""

import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ShiftChangeRequest, ShiftTemplate, StaffShift, StaffUser
from app.notifications.service import notify
from app.outbox.service import record_domain_event
from app.staff_operations.schemas import (
    ShiftChangeDecisionIn,
    ShiftChangeRequestCreateIn,
    ShiftTemplateCreateIn,
    StaffShiftCreateIn,
    StaffShiftUpdateIn,
)

_ACTIVE_SHIFT_STATUSES = ("scheduled", "published", "completed")


async def create_shift_template(
    session: AsyncSession, *, actor: StaffUser, payload: ShiftTemplateCreateIn
) -> ShiftTemplate:
    template = ShiftTemplate(
        name=payload.name,
        department_id=payload.department_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        break_minutes=payload.break_minutes,
        is_overnight=payload.is_overnight,
        grace_period_minutes=payload.grace_period_minutes,
        created_by=actor.id,
    )
    session.add(template)
    await session.flush()
    return template


async def list_shift_templates(session: AsyncSession) -> list[ShiftTemplate]:
    result = await session.scalars(select(ShiftTemplate).where(ShiftTemplate.is_active.is_(True)))
    return list(result.all())


async def _has_overlap(
    session: AsyncSession,
    *,
    staff_user_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
    exclude_shift_id: uuid.UUID | None = None,
) -> bool:
    stmt = select(StaffShift.id).where(
        StaffShift.staff_user_id == staff_user_id,
        StaffShift.status.in_(_ACTIVE_SHIFT_STATUSES),
        StaffShift.start_at < end_at,
        StaffShift.end_at > start_at,
    )
    if exclude_shift_id is not None:
        stmt = stmt.where(StaffShift.id != exclude_shift_id)
    return (await session.scalar(stmt.limit(1))) is not None


async def create_shift(
    session: AsyncSession,
    *,
    actor: StaffUser,
    payload: StaffShiftCreateIn,
    allow_overlap: bool = False,
) -> StaffShift:
    if payload.end_at <= payload.start_at:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Shift end must be after start."
        )
    if not allow_overlap and await _has_overlap(
        session,
        staff_user_id=payload.staff_user_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This staff member already has an overlapping shift."
        )
    shift = StaffShift(
        staff_user_id=payload.staff_user_id,
        shift_date=payload.shift_date,
        shift_template_id=payload.shift_template_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        department_id=payload.department_id,
        role_on_shift=payload.role_on_shift,
        notes=payload.notes,
        created_by=actor.id,
    )
    session.add(shift)
    await session.flush()
    return shift


async def update_shift(
    session: AsyncSession, *, actor: StaffUser, shift: StaffShift, payload: StaffShiftUpdateIn
) -> StaffShift:
    if shift.version != payload.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This shift was modified by someone else. Reload and try again.",
        )
    new_start = payload.start_at or shift.start_at
    new_end = payload.end_at or shift.end_at
    if new_end <= new_start:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Shift end must be after start."
        )
    if (payload.start_at is not None or payload.end_at is not None) and await _has_overlap(
        session,
        staff_user_id=shift.staff_user_id,
        start_at=new_start,
        end_at=new_end,
        exclude_shift_id=shift.id,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This staff member already has an overlapping shift."
        )
    shift.start_at = new_start
    shift.end_at = new_end
    if payload.role_on_shift is not None:
        shift.role_on_shift = payload.role_on_shift
    if payload.notes is not None:
        shift.notes = payload.notes
    shift.updated_by = actor.id
    shift.version += 1
    await session.flush()
    return shift


async def publish_shift(
    session: AsyncSession, *, actor: StaffUser, shift: StaffShift
) -> StaffShift:
    shift.is_published = True
    shift.published_at = datetime.now(UTC)
    shift.status = "published"
    await session.flush()
    await notify(
        session,
        notification_type="staff.shift_published",
        title="Your shift has been published",
        record_type="staff_shift",
        record_id=shift.id,
        recipient_staff_id=shift.staff_user_id,
        dedup_key=f"staff.shift_published:{shift.id}",
    )
    await record_domain_event(
        session,
        event_type="staff.shift.published",
        aggregate_type="staff_shift",
        aggregate_id=shift.id,
        payload={"staff_user_id": str(shift.staff_user_id)},
    )
    await session.flush()
    return shift


async def list_shifts(
    session: AsyncSession,
    *,
    staff_user_id: uuid.UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> list[StaffShift]:
    stmt = select(StaffShift)
    if staff_user_id:
        stmt = stmt.where(StaffShift.staff_user_id == staff_user_id)
    if start_date:
        stmt = stmt.where(StaffShift.shift_date >= start_date)
    if end_date:
        stmt = stmt.where(StaffShift.shift_date <= end_date)
    stmt = stmt.order_by(StaffShift.shift_date, StaffShift.start_at)
    return list((await session.scalars(stmt)).all())


async def create_change_request(
    session: AsyncSession, *, actor: StaffUser, payload: ShiftChangeRequestCreateIn
) -> ShiftChangeRequest:
    if payload.request_type in ("swap", "cover") and payload.proposed_staff_id is not None:
        proposed = await session.get(StaffUser, payload.proposed_staff_id)
        if (
            proposed is None
            or proposed.deleted_at is not None
            or proposed.account_status != "active"
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Proposed replacement staff must be active."
            )
    request = ShiftChangeRequest(
        shift_id=payload.shift_id,
        requested_by=actor.id,
        request_type=payload.request_type,
        proposed_staff_id=payload.proposed_staff_id,
        reason=payload.reason,
        created_by=actor.id,
    )
    session.add(request)
    await session.flush()
    return request


async def decide_change_request(
    session: AsyncSession,
    *,
    actor: StaffUser,
    request: ShiftChangeRequest,
    payload: ShiftChangeDecisionIn,
) -> ShiftChangeRequest:
    if request.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This request has already been decided."
        )
    request.status = "approved" if payload.approve else "rejected"
    request.decided_by = actor.id
    request.decided_at = datetime.now(UTC)
    request.decision_reason = payload.decision_reason
    if payload.approve:
        shift = await session.get(StaffShift, request.shift_id)
        if shift is not None:
            if request.request_type in ("swap", "cover") and request.proposed_staff_id is not None:
                if await _has_overlap(
                    session,
                    staff_user_id=request.proposed_staff_id,
                    start_at=shift.start_at,
                    end_at=shift.end_at,
                    exclude_shift_id=shift.id,
                ):
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        detail="The proposed replacement already has an overlapping shift.",
                    )
                shift.staff_user_id = request.proposed_staff_id
            await notify(
                session,
                notification_type="staff.shift_changed",
                title="A shift you're on has changed",
                record_type="shift_change_request",
                record_id=request.id,
                recipient_staff_id=shift.staff_user_id,
                dedup_key=f"staff.shift_changed:{request.id}",
            )
    await session.flush()
    return request


async def list_change_requests(
    session: AsyncSession, *, status_filter: str | None
) -> list[ShiftChangeRequest]:
    stmt = select(ShiftChangeRequest)
    if status_filter:
        stmt = stmt.where(ShiftChangeRequest.status == status_filter)
    return list((await session.scalars(stmt)).all())
