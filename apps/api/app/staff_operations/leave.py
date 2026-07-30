"""Leave types and requests — this phase's own instruction section 20.
"No duplicate overlapping approved leave where disallowed" is enforced at
submission time against the requester's own other approved/submitted leave.
"""

import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LeaveRequest, LeaveType, StaffUser
from app.notifications.service import notify
from app.outbox.service import record_domain_event
from app.staff_operations.schemas import LeaveDecisionIn, LeaveRequestCreateIn, LeaveTypeCreateIn

_ACTIVE_LEAVE_STATUSES = ("submitted", "approved")


async def create_leave_type(session: AsyncSession, *, payload: LeaveTypeCreateIn) -> LeaveType:
    leave_type = LeaveType(
        name=payload.name,
        code=payload.code,
        is_paid=payload.is_paid,
        requires_notice_days=payload.requires_notice_days,
        max_consecutive_days=payload.max_consecutive_days,
        allows_carry_forward=payload.allows_carry_forward,
        carry_forward_max_days=payload.carry_forward_max_days,
    )
    session.add(leave_type)
    await session.flush()
    return leave_type


async def list_leave_types(session: AsyncSession) -> list[LeaveType]:
    result = await session.scalars(select(LeaveType).where(LeaveType.is_active.is_(True)))
    return list(result.all())


async def _has_overlapping_leave(
    session: AsyncSession, *, staff_user_id: uuid.UUID, start_date: date, end_date: date
) -> bool:
    existing = await session.scalar(
        select(LeaveRequest.id)
        .where(
            LeaveRequest.staff_user_id == staff_user_id,
            LeaveRequest.status.in_(_ACTIVE_LEAVE_STATUSES),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        .limit(1)
    )
    return existing is not None


async def submit_leave_request(
    session: AsyncSession, *, actor: StaffUser, payload: LeaveRequestCreateIn
) -> LeaveRequest:
    if payload.end_date < payload.start_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Leave end must be on or after start."
        )
    leave_type = await session.get(LeaveType, payload.leave_type_id)
    if leave_type is None or not leave_type.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Leave type not found.")
    if leave_type.max_consecutive_days is not None:
        span_days = (payload.end_date - payload.start_date).days + 1
        if span_days > leave_type.max_consecutive_days:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"This leave type allows at most "
                f"{leave_type.max_consecutive_days} consecutive days.",
            )
    if await _has_overlapping_leave(
        session, staff_user_id=actor.id, start_date=payload.start_date, end_date=payload.end_date
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="You already have an overlapping leave request."
        )
    leave_request = LeaveRequest(
        staff_user_id=actor.id,
        leave_type_id=payload.leave_type_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_partial_day=payload.is_partial_day,
        partial_day_portion=payload.partial_day_portion,
        reason=payload.reason,
        status="submitted",
        created_by=actor.id,
    )
    session.add(leave_request)
    await session.flush()
    await record_domain_event(
        session,
        event_type="staff.leave.submitted",
        aggregate_type="leave_request",
        aggregate_id=leave_request.id,
        payload={"staff_user_id": str(actor.id)},
    )
    await session.flush()
    return leave_request


async def decide_leave_request(
    session: AsyncSession,
    *,
    actor: StaffUser,
    leave_request: LeaveRequest,
    payload: LeaveDecisionIn,
) -> LeaveRequest:
    if leave_request.status != "submitted":
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This request has already been decided."
        )
    leave_request.status = "approved" if payload.approve else "rejected"
    leave_request.approver_id = actor.id
    leave_request.decision_reason = payload.decision_reason
    leave_request.decided_at = datetime.now(UTC)
    await session.flush()
    await notify(
        session,
        notification_type="staff.leave_decided",
        title=f"Your leave request was {leave_request.status}",
        record_type="leave_request",
        record_id=leave_request.id,
        recipient_staff_id=leave_request.staff_user_id,
        dedup_key=f"staff.leave_decided:{leave_request.id}",
    )
    await record_domain_event(
        session,
        event_type="staff.leave.approved" if payload.approve else "staff.leave.rejected",
        aggregate_type="leave_request",
        aggregate_id=leave_request.id,
        payload={"staff_user_id": str(leave_request.staff_user_id)},
    )
    await session.flush()
    return leave_request


async def withdraw_leave_request(
    session: AsyncSession, *, actor: StaffUser, leave_request: LeaveRequest
) -> LeaveRequest:
    if leave_request.status not in ("draft", "submitted"):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Only a draft or submitted request can be withdrawn."
        )
    leave_request.status = "withdrawn"
    await session.flush()
    return leave_request


async def list_leave_requests(
    session: AsyncSession, *, staff_user_id: uuid.UUID | None, status_filter: str | None
) -> list[LeaveRequest]:
    stmt = select(LeaveRequest)
    if staff_user_id:
        stmt = stmt.where(LeaveRequest.staff_user_id == staff_user_id)
    if status_filter:
        stmt = stmt.where(LeaveRequest.status == status_filter)
    stmt = stmt.order_by(LeaveRequest.start_date.desc())
    return list((await session.scalars(stmt)).all())
