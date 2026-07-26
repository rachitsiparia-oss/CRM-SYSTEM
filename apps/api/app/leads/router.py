import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.customers.schemas import CustomerListItemOut, CustomerOut
from app.db.models import Lead, LeadActivity, LeadFollowUp, StaffUser
from app.db.session import get_db
from app.leads import service
from app.leads.schemas import (
    ConversionExecuteIn,
    ConversionPreviewOut,
    DuplicateLeadMatchOut,
    LeadActivityIn,
    LeadActivityOut,
    LeadArchiveIn,
    LeadAssignIn,
    LeadCreateIn,
    LeadFollowUpCompleteIn,
    LeadFollowUpCreateIn,
    LeadFollowUpOut,
    LeadFollowUpRescheduleIn,
    LeadListItemOut,
    LeadOut,
    LeadTransitionIn,
    LeadUpdateIn,
)
from app.permissions.dependencies import require_permission
from app.shared.normalization import NormalizationError, normalize_email, normalize_phone

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])

_SORT_ALLOWLIST = {"created_at", "next_follow_up_at", "priority", "estimated_value_minor"}


async def _get_lead_or_404(session: AsyncSession, lead_id: uuid.UUID) -> Lead:
    lead = await session.scalar(select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None)))
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    return lead


@router.get("")
async def list_leads(
    request: Request,
    _actor: StaffUser = Depends(require_permission("leads.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
    lead_status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assigned_staff_id: uuid.UUID | None = Query(default=None),
    unassigned: bool = Query(default=False),
    overdue_follow_up: bool = Query(default=False),
    sort: str = Query(default="created_at"),
) -> PaginatedResponse[LeadListItemOut]:
    if sort not in _SORT_ALLOWLIST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort column."
        )

    stmt = select(Lead).where(Lead.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(Lead).where(Lead.deleted_at.is_(None))

    if search:
        pattern = f"%{search}%"
        clause = or_(
            Lead.display_name.ilike(pattern),
            Lead.lead_number.ilike(pattern),
            Lead.organization_name.ilike(pattern),
            Lead.phone_e164.ilike(pattern),
            Lead.email.ilike(pattern),
        )
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if lead_status:
        stmt = stmt.where(Lead.status == lead_status)
        count_stmt = count_stmt.where(Lead.status == lead_status)
    if source:
        stmt = stmt.where(Lead.source == source)
        count_stmt = count_stmt.where(Lead.source == source)
    if priority:
        stmt = stmt.where(Lead.priority == priority)
        count_stmt = count_stmt.where(Lead.priority == priority)
    if assigned_staff_id:
        stmt = stmt.where(Lead.assigned_staff_id == assigned_staff_id)
        count_stmt = count_stmt.where(Lead.assigned_staff_id == assigned_staff_id)
    if unassigned:
        stmt = stmt.where(Lead.assigned_staff_id.is_(None))
        count_stmt = count_stmt.where(Lead.assigned_staff_id.is_(None))
    if overdue_follow_up:
        now = datetime.now(UTC)
        clause = Lead.next_follow_up_at.is_not(None) & (Lead.next_follow_up_at < now)
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)

    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(getattr(Lead, sort).desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    data = [LeadListItemOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/duplicates")
async def check_duplicate_leads(
    request: Request,
    _actor: StaffUser = Depends(require_permission("leads.view")),
    session: AsyncSession = Depends(get_db),
    phone: str | None = Query(default=None),
    email: str | None = Query(default=None),
    exclude_lead_id: uuid.UUID | None = Query(default=None),
) -> DataResponse[list[DuplicateLeadMatchOut]]:
    try:
        normalized_phone = normalize_phone(phone)
        normalized_email = normalize_email(email)
    except NormalizationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    matches = await service.find_duplicate_leads(
        session, phone=normalized_phone, email=normalized_email, exclude_id=exclude_lead_id
    )
    data = [
        DuplicateLeadMatchOut(lead=LeadListItemOut.model_validate(lead), match_reasons=reasons)
        for lead, reasons in matches
    ]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_lead(
    request: Request,
    payload: LeadCreateIn,
    actor: StaffUser = Depends(require_permission("leads.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadOut]:
    lead = await service.create_lead(session, actor=actor, payload=payload, request=request)
    return DataResponse(data=LeadOut.model_validate(lead), meta=request_meta(request))


@router.get("/{lead_id}")
async def get_lead(
    request: Request,
    lead_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("leads.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadOut]:
    lead = await _get_lead_or_404(session, lead_id)
    return DataResponse(data=LeadOut.model_validate(lead), meta=request_meta(request))


@router.patch("/{lead_id}")
async def update_lead(
    request: Request,
    lead_id: uuid.UUID,
    payload: LeadUpdateIn,
    actor: StaffUser = Depends(require_permission("leads.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadOut]:
    lead = await _get_lead_or_404(session, lead_id)
    lead = await service.update_lead(
        session, actor=actor, lead=lead, payload=payload, request=request
    )
    return DataResponse(data=LeadOut.model_validate(lead), meta=request_meta(request))


@router.delete("/{lead_id}")
async def archive_lead(
    request: Request,
    lead_id: uuid.UUID,
    payload: LeadArchiveIn,
    actor: StaffUser = Depends(require_permission("leads.archive")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    lead = await _get_lead_or_404(session, lead_id)
    await service.archive_lead(
        session, actor=actor, lead=lead, reason=payload.reason, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/{lead_id}/restore")
async def restore_lead(
    request: Request,
    lead_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("leads.restore")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadOut]:
    lead = await session.scalar(select(Lead).where(Lead.id == lead_id))
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    await service.restore_lead(session, actor=actor, lead=lead, request=request)
    return DataResponse(data=LeadOut.model_validate(lead), meta=request_meta(request))


@router.post("/{lead_id}/assign")
async def assign_lead(
    request: Request,
    lead_id: uuid.UUID,
    payload: LeadAssignIn,
    actor: StaffUser = Depends(require_permission("leads.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadOut]:
    lead = await _get_lead_or_404(session, lead_id)
    await service.assign_lead(
        session,
        actor=actor,
        lead=lead,
        assigned_staff_id=payload.assigned_staff_id,
        request=request,
    )
    return DataResponse(data=LeadOut.model_validate(lead), meta=request_meta(request))


@router.post("/{lead_id}/transition")
async def transition_lead(
    request: Request,
    lead_id: uuid.UUID,
    payload: LeadTransitionIn,
    actor: StaffUser = Depends(require_permission("leads.transition")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadOut]:
    lead = await _get_lead_or_404(session, lead_id)
    await service.transition_lead(
        session,
        actor=actor,
        lead=lead,
        new_status=payload.new_status,
        reason=payload.reason,
        lost_reason=payload.lost_reason,
        request=request,
    )
    return DataResponse(data=LeadOut.model_validate(lead), meta=request_meta(request))


@router.post("/{lead_id}/do-not-contact")
async def set_do_not_contact(
    request: Request,
    lead_id: uuid.UUID,
    value: bool = Query(...),
    actor: StaffUser = Depends(require_permission("leads.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadOut]:
    lead = await _get_lead_or_404(session, lead_id)
    await service.set_do_not_contact(session, actor=actor, lead=lead, value=value, request=request)
    return DataResponse(data=LeadOut.model_validate(lead), meta=request_meta(request))


@router.get("/{lead_id}/timeline")
async def get_lead_timeline(
    request: Request,
    lead_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("leads.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
) -> PaginatedResponse[LeadActivityOut]:
    await _get_lead_or_404(session, lead_id)
    stmt = (
        select(LeadActivity)
        .where(LeadActivity.lead_id == lead_id)
        .order_by(LeadActivity.occurred_at.desc())
    )
    count_stmt = (
        select(func.count()).select_from(LeadActivity).where(LeadActivity.lead_id == lead_id)
    )
    total = await session.scalar(count_stmt) or 0
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [LeadActivityOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/{lead_id}/activities", status_code=status.HTTP_201_CREATED)
async def add_activity(
    request: Request,
    lead_id: uuid.UUID,
    payload: LeadActivityIn,
    actor: StaffUser = Depends(require_permission("leads.notes.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadActivityOut]:
    lead = await _get_lead_or_404(session, lead_id)
    activity = await service.add_activity(
        session,
        actor=actor,
        lead=lead,
        activity_type=payload.activity_type,
        summary=payload.summary,
        occurred_at=payload.occurred_at,
        request=request,
    )
    return DataResponse(data=LeadActivityOut.model_validate(activity), meta=request_meta(request))


@router.get("/{lead_id}/follow-ups")
async def list_follow_ups(
    request: Request,
    lead_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("leads.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[LeadFollowUpOut]]:
    await _get_lead_or_404(session, lead_id)
    rows = (
        await session.scalars(
            select(LeadFollowUp)
            .where(LeadFollowUp.lead_id == lead_id)
            .order_by(LeadFollowUp.scheduled_at.desc())
        )
    ).all()
    data = [LeadFollowUpOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/{lead_id}/follow-ups", status_code=status.HTTP_201_CREATED)
async def schedule_follow_up(
    request: Request,
    lead_id: uuid.UUID,
    payload: LeadFollowUpCreateIn,
    actor: StaffUser = Depends(require_permission("leads.followup.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadFollowUpOut]:
    lead = await _get_lead_or_404(session, lead_id)
    follow_up = await service.schedule_follow_up(
        session,
        actor=actor,
        lead=lead,
        scheduled_at=payload.scheduled_at,
        assigned_to=payload.assigned_to,
        purpose=payload.purpose,
        channel=payload.channel,
        request=request,
    )
    return DataResponse(data=LeadFollowUpOut.model_validate(follow_up), meta=request_meta(request))


async def _get_follow_up_or_404(
    session: AsyncSession, lead_id: uuid.UUID, follow_up_id: uuid.UUID
) -> LeadFollowUp:
    follow_up = await session.scalar(
        select(LeadFollowUp).where(LeadFollowUp.id == follow_up_id, LeadFollowUp.lead_id == lead_id)
    )
    if follow_up is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found.")
    return follow_up


@router.post("/{lead_id}/follow-ups/{follow_up_id}/complete")
async def complete_follow_up(
    request: Request,
    lead_id: uuid.UUID,
    follow_up_id: uuid.UUID,
    payload: LeadFollowUpCompleteIn,
    actor: StaffUser = Depends(require_permission("leads.followup.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadFollowUpOut]:
    lead = await _get_lead_or_404(session, lead_id)
    follow_up = await _get_follow_up_or_404(session, lead_id, follow_up_id)
    follow_up = await service.complete_follow_up(
        session,
        actor=actor,
        lead=lead,
        follow_up=follow_up,
        outcome=payload.outcome,
        request=request,
    )
    return DataResponse(data=LeadFollowUpOut.model_validate(follow_up), meta=request_meta(request))


@router.post("/{lead_id}/follow-ups/{follow_up_id}/reschedule")
async def reschedule_follow_up(
    request: Request,
    lead_id: uuid.UUID,
    follow_up_id: uuid.UUID,
    payload: LeadFollowUpRescheduleIn,
    actor: StaffUser = Depends(require_permission("leads.followup.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LeadFollowUpOut]:
    lead = await _get_lead_or_404(session, lead_id)
    follow_up = await _get_follow_up_or_404(session, lead_id, follow_up_id)
    follow_up = await service.reschedule_follow_up(
        session,
        actor=actor,
        lead=lead,
        follow_up=follow_up,
        scheduled_at=payload.scheduled_at,
        reason=payload.reason,
        request=request,
    )
    return DataResponse(data=LeadFollowUpOut.model_validate(follow_up), meta=request_meta(request))


@router.get("/{lead_id}/convert/preview")
async def preview_conversion(
    request: Request,
    lead_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("leads.convert")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ConversionPreviewOut]:
    lead = await _get_lead_or_404(session, lead_id)
    result = await service.preview_conversion(session, lead=lead)
    out = ConversionPreviewOut(
        lead=LeadOut.model_validate(lead),
        possible_customer_matches=[
            CustomerListItemOut.model_validate(c) for c in result["possible_customer_matches"]
        ],
        will_create_new_customer=result["will_create_new_customer"],
    )
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/{lead_id}/convert")
async def execute_conversion(
    request: Request,
    lead_id: uuid.UUID,
    payload: ConversionExecuteIn,
    actor: StaffUser = Depends(require_permission("leads.convert")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerOut]:
    lead = await _get_lead_or_404(session, lead_id)
    customer = await service.execute_conversion(
        session,
        actor=actor,
        lead=lead,
        existing_customer_id=payload.existing_customer_id,
        idempotency_key=payload.idempotency_key,
        request=request,
    )
    return DataResponse(data=CustomerOut.model_validate(customer), meta=request_meta(request))
