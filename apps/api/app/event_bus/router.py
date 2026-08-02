from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import request_meta
from app.db.models import StaffUser
from app.db.session import get_db
from app.event_bus import service
from app.event_bus.schemas import OutboxEventOut
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/event-log", tags=["event-log"])


@router.get("")
async def list_events(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    event_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("event_log.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[OutboxEventOut]:
    rows, total = await service.list_outbox_events(
        session, status=status_filter, event_type=event_type, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=[OutboxEventOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )
