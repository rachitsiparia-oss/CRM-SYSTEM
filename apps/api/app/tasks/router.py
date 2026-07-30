import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import StaffUser, TaskRecord
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.permissions.service import has_permission
from app.tasks import service
from app.tasks.schemas import (
    TaskAssignIn,
    TaskCreateIn,
    TaskOut,
    TaskTransitionIn,
    TaskUpdateIn,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


async def _get_task_or_404(session: AsyncSession, task_id: uuid.UUID) -> TaskRecord:
    task = await service.get_task(session, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


@router.get("")
async def list_tasks(
    request: Request,
    actor: StaffUser = Depends(require_permission("tasks.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    task_status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assigned_staff_id: uuid.UUID | None = Query(default=None),
    view: str | None = Query(default=None, description="mine|due_today|overdue|blocked"),
    search: str | None = Query(default=None, max_length=200),
) -> PaginatedResponse[TaskOut]:
    stmt = select(TaskRecord)
    count_stmt = select(func.count()).select_from(TaskRecord)

    has_view_all = await has_permission(session, actor.id, "tasks.view_all")
    if not has_view_all:
        clause = or_(TaskRecord.assigned_staff_id == actor.id, TaskRecord.created_by == actor.id)
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    if search:
        pattern = f"%{search}%"
        clause = or_(TaskRecord.title.ilike(pattern), TaskRecord.task_number.ilike(pattern))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if task_status:
        stmt = stmt.where(TaskRecord.status == task_status)
        count_stmt = count_stmt.where(TaskRecord.status == task_status)
    if priority:
        stmt = stmt.where(TaskRecord.priority == priority)
        count_stmt = count_stmt.where(TaskRecord.priority == priority)
    if assigned_staff_id:
        stmt = stmt.where(TaskRecord.assigned_staff_id == assigned_staff_id)
        count_stmt = count_stmt.where(TaskRecord.assigned_staff_id == assigned_staff_id)

    now = datetime.now(UTC)
    if view == "mine":
        stmt = stmt.where(TaskRecord.assigned_staff_id == actor.id)
        count_stmt = count_stmt.where(TaskRecord.assigned_staff_id == actor.id)
    elif view == "due_today":
        clause = func.date(TaskRecord.due_at) == now.date()
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    elif view == "overdue":
        clause = (TaskRecord.due_at < now) & (TaskRecord.status.not_in(("completed", "cancelled")))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    elif view == "blocked":
        stmt = stmt.where(TaskRecord.status == "blocked")
        count_stmt = count_stmt.where(TaskRecord.status == "blocked")

    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(TaskRecord.due_at.asc().nulls_last(), TaskRecord.created_at.desc())
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [TaskOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/{task_id}")
async def get_task(
    task_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("tasks.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TaskOut]:
    task = await _get_task_or_404(session, task_id)
    return DataResponse(data=TaskOut.model_validate(task), meta=request_meta(request))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("tasks.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TaskOut]:
    task = await service.create_task(session, actor=actor, payload=payload)
    return DataResponse(data=TaskOut.model_validate(task), meta=request_meta(request))


@router.patch("/{task_id}")
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("tasks.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TaskOut]:
    task = await _get_task_or_404(session, task_id)
    task = await service.update_task(session, actor=actor, task=task, payload=payload)
    return DataResponse(data=TaskOut.model_validate(task), meta=request_meta(request))


@router.post("/{task_id}/transition")
async def transition_task(
    task_id: uuid.UUID,
    payload: TaskTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("tasks.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TaskOut]:
    task = await _get_task_or_404(session, task_id)
    # `service.transition_task` enforces the target-status-specific
    # permission (e.g. `tasks.complete`/`tasks.delete`/`tasks.reopen`) on
    # top of the base `tasks.update` grant checked above.
    task = await service.transition_task(
        session,
        actor=actor,
        task=task,
        target_status=payload.target_status,
        reason=payload.reason,
        completion_notes=payload.completion_notes,
        blocked_reason=payload.blocked_reason,
    )
    return DataResponse(data=TaskOut.model_validate(task), meta=request_meta(request))


@router.post("/{task_id}/assign")
async def assign_task(
    task_id: uuid.UUID,
    payload: TaskAssignIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("tasks.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TaskOut]:
    task = await _get_task_or_404(session, task_id)
    task = await service.assign_task(
        session,
        actor=actor,
        task=task,
        assigned_staff_id=payload.assigned_staff_id,
        assigned_department_id=payload.assigned_department_id,
        reason=payload.reason,
    )
    return DataResponse(data=TaskOut.model_validate(task), meta=request_meta(request))


@router.delete("/{task_id}")
async def cancel_task(
    task_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("tasks.delete")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TaskOut]:
    task = await _get_task_or_404(session, task_id)
    task = await service.transition_task(
        session, actor=actor, task=task, target_status="cancelled", reason="Cancelled by staff."
    )
    return DataResponse(data=TaskOut.model_validate(task), meta=request_meta(request))
