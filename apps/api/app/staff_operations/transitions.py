"""Onboarding and offboarding — template definitions plus per-staff plan
instances, using the consolidated `StaffTransitionTemplate(Step)`/
`StaffTransitionPlan(Step)` schema (this phase's own instruction sections
15-16, consolidated per the Phase 11 deviations note). Each actionable step
creates a Phase 10 task rather than a parallel tracking mechanism.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    StaffTransitionPlan,
    StaffTransitionStep,
    StaffTransitionTemplate,
    StaffTransitionTemplateStep,
    StaffUser,
    TaskRecord,
)
from app.outbox.service import record_domain_event
from app.staff_operations.schemas import (
    TransitionPlanCreateIn,
    TransitionTemplateCreateIn,
    TransitionTemplateStepCreateIn,
)
from app.tasks.service import generate_task_number


async def create_template(
    session: AsyncSession, *, actor: StaffUser, payload: TransitionTemplateCreateIn
) -> StaffTransitionTemplate:
    template = StaffTransitionTemplate(
        transition_type=payload.transition_type,
        name=payload.name,
        department_id=payload.department_id,
        role_id=payload.role_id,
        created_by=actor.id,
    )
    session.add(template)
    await session.flush()
    return template


async def add_template_step(
    session: AsyncSession,
    *,
    template: StaffTransitionTemplate,
    payload: TransitionTemplateStepCreateIn,
) -> StaffTransitionTemplateStep:
    step = StaffTransitionTemplateStep(
        template_id=template.id,
        step_order=payload.step_order,
        title=payload.title,
        description=payload.description,
        step_type=payload.step_type,
        depends_on_step_id=payload.depends_on_step_id,
        requires_approval=payload.requires_approval,
        related_knowledge_article_id=payload.related_knowledge_article_id,
    )
    session.add(step)
    await session.flush()
    return step


async def list_templates(
    session: AsyncSession, transition_type: str | None
) -> list[StaffTransitionTemplate]:
    stmt = select(StaffTransitionTemplate)
    if transition_type:
        stmt = stmt.where(StaffTransitionTemplate.transition_type == transition_type)
    return list((await session.scalars(stmt)).all())


async def create_plan(
    session: AsyncSession, *, actor: StaffUser, payload: TransitionPlanCreateIn
) -> StaffTransitionPlan:
    plan = StaffTransitionPlan(
        staff_user_id=payload.staff_user_id,
        template_id=payload.template_id,
        transition_type=payload.transition_type,
        initiated_by=actor.id,
        created_by=actor.id,
    )
    session.add(plan)
    await session.flush()

    if payload.template_id is not None:
        template_steps = (
            await session.scalars(
                select(StaffTransitionTemplateStep)
                .where(StaffTransitionTemplateStep.template_id == payload.template_id)
                .order_by(StaffTransitionTemplateStep.step_order)
            )
        ).all()
        step_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for template_step in template_steps:
            step = StaffTransitionStep(
                plan_id=plan.id,
                template_step_id=template_step.id,
                step_order=template_step.step_order,
                title=template_step.title,
                description=template_step.description,
                step_type=template_step.step_type,
                requires_approval=template_step.requires_approval,
                created_by=actor.id,
            )
            session.add(step)
            await session.flush()
            step_id_map[template_step.id] = step.id
            session.add(
                TaskRecord(
                    task_number=generate_task_number(),
                    title=f"{payload.transition_type.title()}: {step.title}",
                    source="system",
                    priority="normal",
                    status="open",
                    assigned_staff_id=payload.staff_user_id,
                    related_type="staff_transition_plan",
                    related_id=plan.id,
                    created_by=actor.id,
                )
            )
        for template_step in template_steps:
            if template_step.depends_on_step_id is not None:
                step_id = step_id_map[template_step.id]
                depends_on_step_id = step_id_map.get(template_step.depends_on_step_id)
                step_row = await session.get(StaffTransitionStep, step_id)
                if step_row is not None:
                    step_row.depends_on_step_id = depends_on_step_id
    await record_domain_event(
        session,
        event_type=f"staff.{payload.transition_type}.started",
        aggregate_type="staff_transition_plan",
        aggregate_id=plan.id,
        payload={"staff_user_id": str(payload.staff_user_id)},
    )
    await session.flush()
    return plan


async def _recalculate_completion(session: AsyncSession, plan: StaffTransitionPlan) -> None:
    steps = (
        await session.scalars(
            select(StaffTransitionStep).where(StaffTransitionStep.plan_id == plan.id)
        )
    ).all()
    if not steps:
        return
    completed = sum(1 for s in steps if s.status in ("completed", "skipped"))
    plan.completion_percentage = int(completed / len(steps) * 100)
    if completed == len(steps):
        plan.status = "completed"
        plan.completed_at = datetime.now(UTC)
        await record_domain_event(
            session,
            event_type=f"staff.{plan.transition_type}.completed",
            aggregate_type="staff_transition_plan",
            aggregate_id=plan.id,
            payload={"staff_user_id": str(plan.staff_user_id)},
        )


async def complete_step(
    session: AsyncSession,
    *,
    actor: StaffUser,
    step: StaffTransitionStep,
    completion_evidence: str | None,
) -> StaffTransitionStep:
    if step.depends_on_step_id is not None:
        dependency = await session.get(StaffTransitionStep, step.depends_on_step_id)
        if dependency is not None and dependency.status not in ("completed", "skipped"):
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="A dependency step must be completed first."
            )
    if step.requires_approval:
        step.status = "in_progress"
        step.completion_evidence = completion_evidence
        step.completed_by = actor.id
    else:
        step.status = "completed"
        step.completed_at = datetime.now(UTC)
        step.completed_by = actor.id
        step.completion_evidence = completion_evidence
    await session.flush()
    plan = await session.get(StaffTransitionPlan, step.plan_id)
    if plan is not None:
        await _recalculate_completion(session, plan)
    await session.flush()
    return step


async def approve_step(
    session: AsyncSession, *, actor: StaffUser, step: StaffTransitionStep
) -> StaffTransitionStep:
    if not step.requires_approval:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="This step does not require approval.")
    step.status = "completed"
    step.completed_at = datetime.now(UTC)
    step.approved_by = actor.id
    step.approved_at = datetime.now(UTC)
    await session.flush()
    plan = await session.get(StaffTransitionPlan, step.plan_id)
    if plan is not None:
        await _recalculate_completion(session, plan)
    await session.flush()
    return step


async def list_plan_steps(session: AsyncSession, plan_id: uuid.UUID) -> list[StaffTransitionStep]:
    result = await session.scalars(
        select(StaffTransitionStep)
        .where(StaffTransitionStep.plan_id == plan_id)
        .order_by(StaffTransitionStep.step_order)
    )
    return list(result.all())


async def get_plan_for_staff(
    session: AsyncSession, *, staff_user_id: uuid.UUID, transition_type: str
) -> StaffTransitionPlan | None:
    result: StaffTransitionPlan | None = await session.scalar(
        select(StaffTransitionPlan)
        .where(
            StaffTransitionPlan.staff_user_id == staff_user_id,
            StaffTransitionPlan.transition_type == transition_type,
            StaffTransitionPlan.status == "in_progress",
        )
        .order_by(StaffTransitionPlan.started_at.desc())
    )
    return result
