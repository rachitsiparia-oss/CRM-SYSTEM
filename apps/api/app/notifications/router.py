import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentStaffUser
from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import Notification, StaffUser
from app.db.session import get_db
from app.notifications import service
from app.notifications.schemas import NotificationBroadcastIn, NotificationOut
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


async def _get_own_notification_or_404(
    session: AsyncSession, *, notification_id: uuid.UUID, staff_id: uuid.UUID
) -> Notification:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.recipient_staff_id != staff_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return notification


@router.get("")
async def list_notifications(
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    unread_only: bool = Query(default=False),
) -> PaginatedResponse[NotificationOut]:
    stmt = select(Notification).where(Notification.recipient_staff_id == actor.id)
    count_stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.recipient_staff_id == actor.id)
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
        count_stmt = count_stmt.where(Notification.read_at.is_(None))

    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(Notification.created_at.desc())
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [NotificationOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/unread-count")
async def unread_count(
    request: Request, actor: CurrentStaffUser, session: AsyncSession = Depends(get_db)
) -> DataResponse[int]:
    count = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.recipient_staff_id == actor.id, Notification.read_at.is_(None))
    )
    return DataResponse(data=count or 0, meta=request_meta(request))


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[NotificationOut]:
    notification = await _get_own_notification_or_404(
        session, notification_id=notification_id, staff_id=actor.id
    )
    notification = await service.mark_read(session, notification=notification)
    return DataResponse(
        data=NotificationOut.model_validate(notification), meta=request_meta(request)
    )


@router.post("/read-all")
async def mark_all_notifications_read(
    request: Request, actor: CurrentStaffUser, session: AsyncSession = Depends(get_db)
) -> DataResponse[int]:
    count = await service.mark_all_read(session, recipient_staff_id=actor.id)
    return DataResponse(data=count, meta=request_meta(request))


@router.post("/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: uuid.UUID,
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[NotificationOut]:
    notification = await _get_own_notification_or_404(
        session, notification_id=notification_id, staff_id=actor.id
    )
    notification = await service.dismiss(session, notification=notification)
    return DataResponse(
        data=NotificationOut.model_validate(notification), meta=request_meta(request)
    )


@router.post("/{notification_id}/action")
async def action_notification(
    notification_id: uuid.UUID,
    request: Request,
    actor: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[NotificationOut]:
    notification = await _get_own_notification_or_404(
        session, notification_id=notification_id, staff_id=actor.id
    )
    notification = await service.mark_actioned(session, notification=notification)
    return DataResponse(
        data=NotificationOut.model_validate(notification), meta=request_meta(request)
    )


@router.post("/broadcast")
async def broadcast_notification(
    payload: NotificationBroadcastIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("notifications.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[NotificationOut]]:
    notifications = await service.broadcast(
        session,
        recipient_staff_ids=payload.recipient_staff_ids,
        title=payload.title,
        body=payload.body,
        priority=payload.priority,
    )
    return DataResponse(
        data=[NotificationOut.model_validate(n) for n in notifications], meta=request_meta(request)
    )
