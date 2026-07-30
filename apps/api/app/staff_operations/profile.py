"""Employment profile CRUD, lifecycle-status transitions, and reporting-line
changes — this phase's own instruction section 12-13. Reporting-cycle
prevention mirrors `app.knowledge.categories`' ancestry-cycle walk.
"""

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    StaffEmploymentProfile,
    StaffReportingHistory,
    StaffStatusHistory,
    StaffUser,
)
from app.notifications.service import notify
from app.outbox.service import record_domain_event
from app.staff_operations.schemas import (
    EmploymentProfileCreateIn,
    EmploymentProfileUpdateIn,
    LifecycleTransitionIn,
)

LIFECYCLE_TRANSITIONS: dict[str, frozenset[str]] = {
    "invited": frozenset({"onboarding", "inactive"}),
    "onboarding": frozenset({"active", "inactive"}),
    "active": frozenset({"on_leave", "suspended", "notice_period", "inactive"}),
    "on_leave": frozenset({"active", "notice_period", "inactive"}),
    "suspended": frozenset({"active", "notice_period", "terminated", "inactive"}),
    "notice_period": frozenset({"terminated", "active"}),
    "inactive": frozenset({"active"}),
    "terminated": frozenset(),
}


def is_lifecycle_transition_allowed(current: str, target: str) -> bool:
    return target in LIFECYCLE_TRANSITIONS.get(current, frozenset())


async def _would_create_reporting_cycle(
    session: AsyncSession, *, staff_user_id: uuid.UUID, proposed_manager_id: uuid.UUID
) -> bool:
    current_id: uuid.UUID | None = proposed_manager_id
    seen: set[uuid.UUID] = set()
    while current_id is not None:
        if current_id == staff_user_id:
            return True
        if current_id in seen:
            return True
        seen.add(current_id)
        manager_profile = await session.scalar(
            select(StaffEmploymentProfile).where(StaffEmploymentProfile.staff_user_id == current_id)
        )
        if manager_profile is None:
            return False
        current_id = manager_profile.reporting_manager_id
    return False


async def get_profile(
    session: AsyncSession, staff_user_id: uuid.UUID
) -> StaffEmploymentProfile | None:
    result: StaffEmploymentProfile | None = await session.scalar(
        select(StaffEmploymentProfile).where(StaffEmploymentProfile.staff_user_id == staff_user_id)
    )
    return result


async def create_profile(
    session: AsyncSession, *, actor: StaffUser, payload: EmploymentProfileCreateIn
) -> StaffEmploymentProfile:
    existing = await get_profile(session, payload.staff_user_id)
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="An employment profile already exists for this staff member.",
        )
    if payload.reporting_manager_id == payload.staff_user_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Staff cannot report to themselves."
        )
    if payload.reporting_manager_id is not None and await _would_create_reporting_cycle(
        session,
        staff_user_id=payload.staff_user_id,
        proposed_manager_id=payload.reporting_manager_id,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This would create a reporting-line cycle."
        )
    profile = StaffEmploymentProfile(
        staff_user_id=payload.staff_user_id,
        lifecycle_status="invited",
        reporting_manager_id=payload.reporting_manager_id,
        secondary_supervisor_id=payload.secondary_supervisor_id,
        work_location=payload.work_location,
        default_shift_template_id=payload.default_shift_template_id,
        joining_date=payload.joining_date,
        probation_end_date=payload.probation_end_date,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        emergency_contact_relation=payload.emergency_contact_relation,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        address_city=payload.address_city,
        address_state=payload.address_state,
        address_postal_code=payload.address_postal_code,
        uniform_size=payload.uniform_size,
        created_by=actor.id,
    )
    session.add(profile)
    await session.flush()
    session.add(
        StaffStatusHistory(
            staff_user_id=payload.staff_user_id,
            previous_status=None,
            new_status="invited",
            actor_id=actor.id,
        )
    )
    await record_domain_event(
        session,
        event_type="staff.profile.updated",
        aggregate_type="staff_employment_profile",
        aggregate_id=profile.id,
        payload={"staff_user_id": str(payload.staff_user_id)},
    )
    await session.flush()
    return profile


async def update_profile(
    session: AsyncSession,
    *,
    actor: StaffUser,
    profile: StaffEmploymentProfile,
    payload: EmploymentProfileUpdateIn,
) -> StaffEmploymentProfile:
    if profile.version != payload.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This profile was modified by someone else. Reload and try again.",
        )
    if (
        payload.reporting_manager_id is not None
        and payload.reporting_manager_id != profile.reporting_manager_id
    ):
        if payload.reporting_manager_id == profile.staff_user_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Staff cannot report to themselves."
            )
        if await _would_create_reporting_cycle(
            session,
            staff_user_id=profile.staff_user_id,
            proposed_manager_id=payload.reporting_manager_id,
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="This would create a reporting-line cycle."
            )
        session.add(
            StaffReportingHistory(
                staff_user_id=profile.staff_user_id,
                previous_manager_id=profile.reporting_manager_id,
                new_manager_id=payload.reporting_manager_id,
                actor_id=actor.id,
            )
        )
        profile.reporting_manager_id = payload.reporting_manager_id
    if payload.secondary_supervisor_id is not None:
        profile.secondary_supervisor_id = payload.secondary_supervisor_id
    if payload.work_location is not None:
        profile.work_location = payload.work_location
    if payload.default_shift_template_id is not None:
        profile.default_shift_template_id = payload.default_shift_template_id
    if payload.probation_end_date is not None:
        profile.probation_end_date = payload.probation_end_date
    if payload.confirmation_date is not None:
        profile.confirmation_date = payload.confirmation_date
    if payload.last_working_date is not None:
        profile.last_working_date = payload.last_working_date
    if payload.emergency_contact_name is not None:
        profile.emergency_contact_name = payload.emergency_contact_name
    if payload.emergency_contact_phone is not None:
        profile.emergency_contact_phone = payload.emergency_contact_phone
    if payload.emergency_contact_relation is not None:
        profile.emergency_contact_relation = payload.emergency_contact_relation
    if payload.address_line1 is not None:
        profile.address_line1 = payload.address_line1
    if payload.address_line2 is not None:
        profile.address_line2 = payload.address_line2
    if payload.address_city is not None:
        profile.address_city = payload.address_city
    if payload.address_state is not None:
        profile.address_state = payload.address_state
    if payload.address_postal_code is not None:
        profile.address_postal_code = payload.address_postal_code
    if payload.uniform_size is not None:
        profile.uniform_size = payload.uniform_size
    if payload.restricted_notes is not None:
        profile.restricted_notes = payload.restricted_notes
    profile.updated_by = actor.id
    profile.version += 1
    await session.flush()
    return profile


async def transition_lifecycle(
    session: AsyncSession,
    *,
    actor: StaffUser,
    profile: StaffEmploymentProfile,
    payload: LifecycleTransitionIn,
) -> StaffEmploymentProfile:
    if not is_lifecycle_transition_allowed(profile.lifecycle_status, payload.target_status):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot move employment status from {profile.lifecycle_status!r} to "
            f"{payload.target_status!r}.",
        )
    previous_status = profile.lifecycle_status
    profile.lifecycle_status = payload.target_status
    if payload.target_status == "terminated" and profile.last_working_date is None:
        profile.last_working_date = date.today()
    await session.flush()
    session.add(
        StaffStatusHistory(
            staff_user_id=profile.staff_user_id,
            previous_status=previous_status,
            new_status=payload.target_status,
            actor_id=actor.id,
            reason=payload.reason,
        )
    )
    await record_domain_event(
        session,
        event_type="staff.status.changed",
        aggregate_type="staff_employment_profile",
        aggregate_id=profile.id,
        payload={"previous_status": previous_status, "new_status": payload.target_status},
    )
    if (
        payload.target_status in ("suspended", "terminated", "inactive")
        and profile.reporting_manager_id
    ):
        await notify(
            session,
            notification_type="staff.status_changed",
            title=f"Employment status changed to {payload.target_status}",
            recipient_staff_id=profile.reporting_manager_id,
            dedup_key=f"staff.status:{profile.id}:{payload.target_status}",
        )
    await session.flush()
    return profile
