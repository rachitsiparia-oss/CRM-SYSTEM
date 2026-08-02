import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import DeadLetterEntry, StaffUser
from app.db.session import get_db
from app.dead_letter import service
from app.dead_letter.errors import DeadLetterError
from app.dead_letter.schemas import DeadLetterEntryOut, IgnoreEntryIn, MarkReplayReadyIn
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/dead-letter", tags=["dead-letter"])


async def _get_or_404(session: AsyncSession, entry_id: uuid.UUID) -> DeadLetterEntry:
    try:
        return await service.get_dead_letter_entry(session, entry_id)
    except DeadLetterError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc


@router.get("")
async def list_entries(
    request: Request,
    resolution_status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("dead_letter.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DeadLetterEntryOut]:
    rows, total = await service.list_dead_letter_entries(
        session,
        resolution_status=resolution_status,
        source_type=source_type,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return PaginatedResponse(
        data=[DeadLetterEntryOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/{entry_id}")
async def get_entry(
    entry_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("dead_letter.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DeadLetterEntryOut]:
    entry = await _get_or_404(session, entry_id)
    return DataResponse(data=DeadLetterEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/{entry_id}/investigate")
async def mark_investigating(
    entry_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("dead_letter.replay")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DeadLetterEntryOut]:
    entry = await _get_or_404(session, entry_id)
    entry = await service.mark_investigating(session, entry=entry, actor=actor)
    return DataResponse(data=DeadLetterEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/{entry_id}/mark-replay-ready")
async def mark_replay_ready(
    entry_id: uuid.UUID,
    payload: MarkReplayReadyIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("dead_letter.replay")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DeadLetterEntryOut]:
    entry = await _get_or_404(session, entry_id)
    entry = await service.mark_replay_ready(session, entry=entry, actor=actor, notes=payload.notes)
    return DataResponse(data=DeadLetterEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/{entry_id}/ignore")
async def ignore_entry(
    entry_id: uuid.UUID,
    payload: IgnoreEntryIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("dead_letter.replay")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DeadLetterEntryOut]:
    entry = await _get_or_404(session, entry_id)
    entry = await service.ignore_entry(session, entry=entry, actor=actor, reason=payload.reason)
    return DataResponse(data=DeadLetterEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/{entry_id}/replay")
async def replay_entry(
    entry_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("dead_letter.replay")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DeadLetterEntryOut]:
    entry = await _get_or_404(session, entry_id)
    try:
        await service.replay_entry(session, entry=entry, actor=actor)
    except DeadLetterError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=DeadLetterEntryOut.model_validate(entry), meta=request_meta(request))
