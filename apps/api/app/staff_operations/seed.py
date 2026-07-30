"""Idempotent development seed data for Staff Operations — shift
templates, leave types, training courses, skills, and onboarding/
offboarding templates, plus one employment profile for the single
bootstrapped owner account. No dummy 65-person staff roster is seeded
here — `app.db.seed`'s own note explains why: every `staff_users` row
needs a real Supabase Auth identity, and only the bootstrapped owner
exists in this environment. Do not seed fake identity documents.
"""

from datetime import date, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    LeaveType,
    ShiftTemplate,
    Skill,
    StaffTransitionTemplate,
    StaffUser,
    TrainingCourse,
)
from app.staff_operations.leave import create_leave_type
from app.staff_operations.profile import create_profile, get_profile
from app.staff_operations.schemas import (
    EmploymentProfileCreateIn,
    LeaveTypeCreateIn,
    ShiftTemplateCreateIn,
    SkillCreateIn,
    TrainingCourseCreateIn,
    TransitionTemplateCreateIn,
    TransitionTemplateStepCreateIn,
)
from app.staff_operations.shifts import create_shift_template
from app.staff_operations.skills import create_skill
from app.staff_operations.training import create_course
from app.staff_operations.transitions import add_template_step, create_template

_SHIFT_TEMPLATES: tuple[tuple[str, time, time, int, bool], ...] = (
    ("Morning Shift", time(8, 0), time(16, 0), 30, False),
    ("Evening Shift", time(16, 0), time(0, 0), 30, False),
    ("Overnight Shift", time(22, 0), time(6, 0), 30, True),
)

_LEAVE_TYPES: tuple[tuple[str, str, bool, int, int | None], ...] = (
    ("Casual Leave", "CL", True, 1, 12),
    ("Sick Leave", "SL", True, 0, 12),
    ("Earned Leave", "EL", True, 7, 21),
    ("Unpaid Leave", "LWP", False, 3, None),
)

_TRAINING_COURSES: tuple[tuple[str, str, str, bool, int], ...] = (
    ("Food Safety Fundamentals", "TRN-FOOD-SAFETY", "food_safety", True, 70),
    ("Fire and Emergency Safety", "TRN-FIRE-SAFETY", "safety", True, 70),
    ("Customer Service Excellence", "TRN-CUST-SVC", "service", False, 60),
    ("POS and Order Workflow", "TRN-POS", "operations", False, 60),
)

_SKILLS: tuple[tuple[str, str], ...] = (
    ("POS Operation", "operations"),
    ("Reservation Handling", "operations"),
    ("Food Preparation Station", "kitchen"),
    ("Inventory Receiving", "inventory"),
    ("Allergy Protocol", "food_safety"),
    ("First Aid", "safety"),
)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def seed_shift_templates(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return
    for name, start, end, break_minutes, is_overnight in _SHIFT_TEMPLATES:
        existing = await session.scalar(select(ShiftTemplate).where(ShiftTemplate.name == name))
        if existing is not None:
            continue

        await create_shift_template(
            session,
            actor=actor,
            payload=ShiftTemplateCreateIn(
                name=name,
                start_time=start,
                end_time=end,
                break_minutes=break_minutes,
                is_overnight=is_overnight,
            ),
        )


async def seed_leave_types(session: AsyncSession) -> None:

    for name, code, is_paid, notice_days, max_days in _LEAVE_TYPES:
        existing = await session.scalar(select(LeaveType).where(LeaveType.code == code))
        if existing is not None:
            continue
        await create_leave_type(
            session,
            payload=LeaveTypeCreateIn(
                name=name,
                code=code,
                is_paid=is_paid,
                requires_notice_days=notice_days,
                max_consecutive_days=max_days,
            ),
        )


async def seed_training_courses(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    for title, code, category, is_mandatory, passing_score in _TRAINING_COURSES:
        existing = await session.scalar(select(TrainingCourse).where(TrainingCourse.code == code))
        if existing is not None:
            continue
        await create_course(
            session,
            actor=actor,
            payload=TrainingCourseCreateIn(
                code=code,
                title=title,
                category=category,
                is_mandatory=is_mandatory,
                passing_score=passing_score,
            ),
        )


async def seed_skills(session: AsyncSession) -> None:

    for name, category in _SKILLS:
        existing = await session.scalar(select(Skill).where(Skill.name == name))
        if existing is not None:
            continue
        await create_skill(session, SkillCreateIn(name=name, category=category))


async def seed_transition_templates(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    existing_onboarding = await session.scalar(
        select(StaffTransitionTemplate).where(StaffTransitionTemplate.name == "Standard Onboarding")
    )
    if existing_onboarding is None:
        template = await create_template(
            session,
            actor=actor,
            payload=TransitionTemplateCreateIn(
                transition_type="onboarding", name="Standard Onboarding"
            ),
        )
        steps: tuple[tuple[int, str, str], ...] = (
            (1, "Profile completion", "profile_completion"),
            (2, "Document submission", "document_submission"),
            (3, "Policy acknowledgement", "policy_acknowledgement"),
            (4, "Food safety training", "training"),
            (5, "Department induction", "department_induction"),
            (6, "System access setup", "system_access"),
            (7, "Manager sign-off", "manager_signoff"),
        )
        for order, title, step_type in steps:
            await add_template_step(
                session,
                template=template,
                payload=TransitionTemplateStepCreateIn(
                    step_order=order,
                    title=title,
                    step_type=step_type,
                    requires_approval=(step_type == "manager_signoff"),
                ),
            )

    existing_offboarding = await session.scalar(
        select(StaffTransitionTemplate).where(
            StaffTransitionTemplate.name == "Standard Offboarding"
        )
    )
    if existing_offboarding is None:
        template = await create_template(
            session,
            actor=actor,
            payload=TransitionTemplateCreateIn(
                transition_type="offboarding", name="Standard Offboarding"
            ),
        )
        offboarding_steps: tuple[tuple[int, str, str], ...] = (
            (1, "Access revocation request", "access_revocation"),
            (2, "Asset return", "asset_return"),
            (3, "Handover", "handover"),
            (4, "Final shift", "final_shift"),
            (5, "Exit checklist", "exit_checklist"),
        )
        for order, title, step_type in offboarding_steps:
            await add_template_step(
                session,
                template=template,
                payload=TransitionTemplateStepCreateIn(
                    step_order=order, title=title, step_type=step_type
                ),
            )


async def seed_owner_employment_profile(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return
    existing = await get_profile(session, actor.id)
    if existing is not None:
        return
    await create_profile(
        session,
        actor=actor,
        payload=EmploymentProfileCreateIn(staff_user_id=actor.id, joining_date=date(2024, 1, 1)),
    )


async def seed_staff_operations(session: AsyncSession) -> None:
    await seed_shift_templates(session)
    await seed_leave_types(session)
    await seed_training_courses(session)
    await seed_skills(session)
    await seed_transition_templates(session)
    await seed_owner_employment_profile(session)
