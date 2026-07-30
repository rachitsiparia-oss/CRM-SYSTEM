"""Task creation, assignment, status transitions, and recurring-instance
generation. Kept out of the router for the same reason as every other
domain service in this codebase.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StaffUser, TaskAssignment, TaskRecord, TaskStatusHistory
from app.notifications.service import notify
from app.outbox.service import record_domain_event
from app.permissions.service import has_permission
from app.tasks.schemas import TaskCreateIn, TaskUpdateIn
from app.tasks.states import is_task_transition_allowed

# Individually-permission-gated targets — same treatment
# `app.reservations.service._GATED_TRANSITIONS` gives `cancelled`/
# `completed`; every other allowed transition only needs the base
# `tasks.update` grant already checked by the router's `require_permission`
# dependency.
_GATED_TRANSITIONS: dict[str, str] = {
    "completed": "tasks.complete",
    "cancelled": "tasks.delete",
    "open": "tasks.reopen",
}


def generate_task_number() -> str:
    return f"TASK-{uuid.uuid4().hex[:8].upper()}"


async def get_task(session: AsyncSession, task_id: uuid.UUID) -> TaskRecord | None:
    return await session.get(TaskRecord, task_id)


async def create_task(
    session: AsyncSession, *, actor: StaffUser, payload: TaskCreateIn
) -> TaskRecord:
    if payload.is_recurring_template and payload.recurrence_rule is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A recurring task template requires a recurrence rule.",
        )
    task = TaskRecord(
        task_number=generate_task_number(),
        title=payload.title,
        description=payload.description,
        source=payload.source,
        priority=payload.priority,
        status="open",
        due_at=payload.due_at,
        assigned_staff_id=payload.assigned_staff_id,
        assigned_department_id=payload.assigned_department_id,
        related_type=payload.related_type,
        related_id=payload.related_id,
        is_recurring_template=payload.is_recurring_template,
        recurrence_rule=payload.recurrence_rule.model_dump(mode="json")
        if payload.recurrence_rule
        else None,
        idempotency_key=payload.idempotency_key,
        created_by=actor.id,
    )
    session.add(task)
    await session.flush()
    session.add(
        TaskStatusHistory(
            task_id=task.id, previous_status=None, new_status="open", actor_id=actor.id
        )
    )
    if payload.assigned_staff_id is not None:
        session.add(
            TaskAssignment(
                task_id=task.id,
                previous_assignee_id=None,
                new_assignee_id=payload.assigned_staff_id,
                actor_id=actor.id,
            )
        )
        await notify(
            session,
            notification_type="task.assigned",
            title=f"Task assigned: {task.title}",
            record_type="task",
            record_id=task.id,
            recipient_staff_id=payload.assigned_staff_id,
            dedup_key=f"task.assigned:{task.id}:{payload.assigned_staff_id}",
        )
    await record_domain_event(
        session,
        event_type="task.created",
        aggregate_type="task",
        aggregate_id=task.id,
        payload={"task_number": task.task_number, "source": task.source},
    )
    await session.flush()
    return task


async def update_task(
    session: AsyncSession, *, actor: StaffUser, task: TaskRecord, payload: TaskUpdateIn
) -> TaskRecord:
    if task.version != payload.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This task was modified by someone else. Reload and try again.",
        )
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.due_at is not None:
        task.due_at = payload.due_at
    task.updated_by = actor.id
    task.version += 1
    await session.flush()
    return task


async def transition_task(
    session: AsyncSession,
    *,
    actor: StaffUser,
    task: TaskRecord,
    target_status: str,
    reason: str | None = None,
    completion_notes: str | None = None,
    blocked_reason: str | None = None,
) -> TaskRecord:
    if not is_task_transition_allowed(task.status, target_status):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot move a task from {task.status!r} to {target_status!r}.",
        )
    required_permission = _GATED_TRANSITIONS.get(target_status)
    if required_permission is not None and not await has_permission(
        session, actor.id, required_permission
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to move a task to {target_status!r}.",
        )
    if target_status == "blocked" and not blocked_reason:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A reason is required to mark a task blocked.",
        )
    previous_status = task.status
    task.status = target_status
    now = datetime.now(UTC)
    if target_status == "completed":
        task.completed_at = now
        task.completed_by = actor.id
        task.completion_notes = completion_notes
    if target_status == "blocked":
        task.blocked_reason = blocked_reason
    if target_status == "open" and previous_status in ("completed", "cancelled", "blocked"):
        task.completed_at = None
        task.completed_by = None
        task.blocked_reason = None

    session.add(
        TaskStatusHistory(
            task_id=task.id,
            previous_status=previous_status,
            new_status=target_status,
            actor_id=actor.id,
            reason=reason,
        )
    )
    await record_domain_event(
        session,
        event_type="task.status_changed",
        aggregate_type="task",
        aggregate_id=task.id,
        payload={"previous_status": previous_status, "new_status": target_status},
    )
    await session.flush()
    return task


async def assign_task(
    session: AsyncSession,
    *,
    actor: StaffUser,
    task: TaskRecord,
    assigned_staff_id: uuid.UUID | None,
    assigned_department_id: uuid.UUID | None,
    reason: str | None = None,
) -> TaskRecord:
    if assigned_staff_id is not None:
        assignee = await session.get(StaffUser, assigned_staff_id)
        if (
            assignee is None
            or assignee.deleted_at is not None
            or assignee.account_status != "active"
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Cannot assign a task to an inactive or missing staff member.",
            )
    previous_assignee_id = task.assigned_staff_id
    task.assigned_staff_id = assigned_staff_id
    task.assigned_department_id = assigned_department_id
    session.add(
        TaskAssignment(
            task_id=task.id,
            previous_assignee_id=previous_assignee_id,
            new_assignee_id=assigned_staff_id,
            actor_id=actor.id,
            reason=reason,
        )
    )
    if assigned_staff_id is not None:
        await notify(
            session,
            notification_type="task.assigned",
            title=f"Task assigned: {task.title}",
            record_type="task",
            record_id=task.id,
            recipient_staff_id=assigned_staff_id,
            dedup_key=f"task.assigned:{task.id}:{assigned_staff_id}",
        )
    await session.flush()
    return task


def _add_months(dt: datetime, months: int) -> datetime:
    total_month_index = dt.month - 1 + months
    year = dt.year + total_month_index // 12
    month = total_month_index % 12 + 1
    day = min(
        dt.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return dt.replace(year=year, month=month, day=day)


def _next_due_at(rule: dict[str, Any], *, after: datetime) -> datetime:
    interval = rule.get("interval", 1)
    frequency = rule["frequency"]
    if frequency == "daily":
        return after + timedelta(days=interval)
    if frequency == "weekly":
        return after + timedelta(weeks=interval)
    return _add_months(after, interval)


async def generate_due_recurring_tasks(
    session: AsyncSession, *, now: datetime | None = None, batch_size: int = 50
) -> list[uuid.UUID]:
    """Explicit engine entry point (CLAUDE.md section 14) — spawns the next
    dated instance of every recurring template whose next occurrence is
    due. Idempotency key `{parent_task_id}:{due_date}` prevents a
    duplicate instance if this is invoked more than once for the same
    window."""
    now = now or datetime.now(UTC)
    templates = (
        await session.scalars(
            select(TaskRecord)
            .where(TaskRecord.is_recurring_template.is_(True), TaskRecord.status == "open")
            .limit(batch_size)
        )
    ).all()

    created_ids: list[uuid.UUID] = []
    for template in templates:
        assert template.recurrence_rule is not None
        last_generated = template.next_occurrence_generated_at or template.created_at
        next_due = _next_due_at(template.recurrence_rule, after=last_generated)
        end_date_raw = template.recurrence_rule.get("end_date")
        if end_date_raw and datetime.fromisoformat(end_date_raw) < next_due:
            continue
        if next_due > now:
            continue

        idempotency_key = f"{template.id}:{next_due.date().isoformat()}"
        insert_stmt = (
            pg_insert(TaskRecord)
            .values(
                id=uuid.uuid4(),
                task_number=generate_task_number(),
                title=template.title,
                description=template.description,
                source="recurring",
                priority=template.priority,
                status="open",
                due_at=next_due,
                assigned_staff_id=template.assigned_staff_id,
                assigned_department_id=template.assigned_department_id,
                related_type=template.related_type,
                related_id=template.related_id,
                parent_task_id=template.id,
                idempotency_key=idempotency_key,
                created_by=template.created_by,
            )
            .on_conflict_do_nothing(
                index_elements=["idempotency_key"], index_where=text("idempotency_key IS NOT NULL")
            )
            .returning(TaskRecord.id)
        )
        result = await session.execute(insert_stmt)
        inserted_id = result.scalar_one_or_none()
        template.next_occurrence_generated_at = next_due
        if inserted_id is not None:
            created_ids.append(inserted_id)
        await session.flush()
    return created_ids
