"""Complaint and SLA-policy API — GROWTH_AND_INTELLIGENCE.md section 12.

`complaints.view` sees only complaints assigned to the actor (staff or
department); `complaints.view_all` bypasses that scope. HR-sensitive
complaints additionally require `complaints.hr_sensitive.read`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.complaints import analytics, service, sla
from app.complaints.errors import ComplaintError
from app.complaints.schemas import (
    ComplaintAnalyticsOut,
    ComplaintAssignIn,
    ComplaintCreateIn,
    ComplaintEscalateIn,
    ComplaintEscalationOut,
    ComplaintFollowUpOut,
    ComplaintLinkCreateIn,
    ComplaintLinkOut,
    ComplaintNoteOut,
    ComplaintOut,
    ComplaintTransitionIn,
    ComplaintUpdateIn,
    FollowUpCompleteIn,
    FollowUpCreateIn,
    NoteCreateIn,
    RootCauseUpdateIn,
    SlaPolicyCreateIn,
    SlaPolicyOut,
    SlaPolicyUpdateIn,
    TimelineEntryOut,
)
from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import Complaint, ComplaintFollowUp, SlaPolicy, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.permissions.service import has_permission
from app.service_recovery import service as recovery_service
from app.service_recovery.schemas import RecoveryActionOut, RecoveryActionProposeIn

router = APIRouter(prefix="/api/v1/complaints", tags=["complaints"])


async def _get_complaint_or_404(session: AsyncSession, complaint_id: uuid.UUID) -> Complaint:
    complaint = await service.get_complaint(session, complaint_id)
    if complaint is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Complaint not found.")
    return complaint


async def _authorize_complaint_access(
    session: AsyncSession, *, actor: StaffUser, complaint: Complaint
) -> None:
    has_view_all = await has_permission(session, actor.id, "complaints.view_all")
    if not has_view_all and complaint.assigned_staff_id != actor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You cannot view this complaint.")
    if complaint.is_hr_sensitive and not await has_permission(
        session, actor.id, "complaints.hr_sensitive.read"
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Viewing this staff-conduct complaint requires additional permission.",
        )


async def _get_follow_up_or_404(
    session: AsyncSession, follow_up_id: uuid.UUID
) -> ComplaintFollowUp:
    row = await session.get(ComplaintFollowUp, follow_up_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Follow-up not found.")
    return row


async def _get_sla_policy_or_404(session: AsyncSession, policy_id: uuid.UUID) -> SlaPolicy:
    policy = await sla.get_sla_policy(session, policy_id)
    if policy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="SLA policy not found.")
    return policy


@router.get("")
async def list_complaints(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    category: str | None = Query(default=None),
    assigned_staff_id: uuid.UUID | None = Query(default=None),
    assigned_department_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    actor: StaffUser = Depends(require_permission("complaints.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ComplaintOut]:
    has_view_all = await has_permission(session, actor.id, "complaints.view_all")
    rows, total = await service.list_complaints(
        session,
        page=page,
        page_size=page_size,
        status=status_filter,
        severity=severity,
        category=category,
        assigned_staff_id=assigned_staff_id,
        assigned_department_id=assigned_department_id,
        customer_id=customer_id,
        scope_staff_id=None if has_view_all else actor.id,
    )
    return PaginatedResponse(
        data=[ComplaintOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_complaint(
    payload: ComplaintCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintOut]:
    complaint = await service.create_complaint(session, actor=actor, payload=payload)
    return DataResponse(data=ComplaintOut.model_validate(complaint), meta=request_meta(request))


@router.get("/analytics")
async def get_complaint_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("complaints.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintAnalyticsOut]:
    result = await analytics.get_analytics(session)
    return DataResponse(data=result, meta=request_meta(request))


@router.get("/sla-policies")
async def list_sla_policies(
    request: Request,
    is_active: bool | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("complaints.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[SlaPolicyOut]]:
    rows = await sla.list_sla_policies(session, is_active=is_active)
    return DataResponse(
        data=[SlaPolicyOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/sla-policies", status_code=status.HTTP_201_CREATED)
async def create_sla_policy(
    payload: SlaPolicyCreateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("complaints.sla.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SlaPolicyOut]:
    policy = await sla.create_sla_policy(session, payload=payload)
    return DataResponse(data=SlaPolicyOut.model_validate(policy), meta=request_meta(request))


@router.patch("/sla-policies/{policy_id}")
async def update_sla_policy(
    policy_id: uuid.UUID,
    payload: SlaPolicyUpdateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("complaints.sla.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SlaPolicyOut]:
    policy = await _get_sla_policy_or_404(session, policy_id)
    policy = await sla.update_sla_policy(session, policy=policy, payload=payload)
    return DataResponse(data=SlaPolicyOut.model_validate(policy), meta=request_meta(request))


@router.post("/sla/run-escalations")
async def run_sla_escalations(
    request: Request,
    _actor: StaffUser = Depends(require_permission("complaints.sla.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, int]]:
    """The deterministic, idempotent SLA-detection/auto-escalation engine
    entry point — manually triggerable until Phase 15 puts it on a
    schedule (CLAUDE.md section 9's "engine, not scheduler" split)."""
    escalations = await service.run_sla_escalations(session)
    return DataResponse(data={"escalations_created": len(escalations)}, meta=request_meta(request))


@router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    return DataResponse(data=ComplaintOut.model_validate(complaint), meta=request_meta(request))


@router.patch("/{complaint_id}")
async def update_complaint(
    complaint_id: uuid.UUID,
    payload: ComplaintUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    complaint = await service.update_complaint(
        session, actor=actor, complaint=complaint, payload=payload
    )
    return DataResponse(data=ComplaintOut.model_validate(complaint), meta=request_meta(request))


@router.post("/{complaint_id}/transition")
async def transition_complaint(
    complaint_id: uuid.UUID,
    payload: ComplaintTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.transition")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    try:
        complaint = await service.transition_complaint(
            session,
            actor=actor,
            complaint=complaint,
            target_status=payload.target_status,
            reason=payload.reason,
            resolution_summary=payload.resolution_summary,
        )
    except ComplaintError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=ComplaintOut.model_validate(complaint), meta=request_meta(request))


@router.post("/{complaint_id}/assign")
async def assign_complaint(
    complaint_id: uuid.UUID,
    payload: ComplaintAssignIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    try:
        complaint = await service.assign_complaint(
            session,
            actor=actor,
            complaint=complaint,
            assigned_staff_id=payload.assigned_staff_id,
            assigned_department_id=payload.assigned_department_id,
            reason=payload.reason,
        )
    except ComplaintError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=ComplaintOut.model_validate(complaint), meta=request_meta(request))


@router.post("/{complaint_id}/escalate", status_code=status.HTTP_201_CREATED)
async def escalate_complaint(
    complaint_id: uuid.UUID,
    payload: ComplaintEscalateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.escalate")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintEscalationOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    try:
        escalation = await service.escalate_complaint(
            session,
            actor=actor,
            complaint=complaint,
            reason=payload.reason,
            new_assigned_staff_id=payload.new_assigned_staff_id,
            new_assigned_department_id=payload.new_assigned_department_id,
        )
    except ComplaintError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=ComplaintEscalationOut.model_validate(escalation), meta=request_meta(request)
    )


@router.post("/{complaint_id}/root-cause")
async def update_root_cause(
    complaint_id: uuid.UUID,
    payload: RootCauseUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    complaint = await service.update_root_cause(
        session,
        actor=actor,
        complaint=complaint,
        root_cause=payload.root_cause,
        notes=payload.notes,
    )
    return DataResponse(data=ComplaintOut.model_validate(complaint), meta=request_meta(request))


@router.post("/{complaint_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_complaint_note(
    complaint_id: uuid.UUID,
    payload: NoteCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintNoteOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    note = await service.add_note(session, actor=actor, complaint=complaint, note=payload.note)
    return DataResponse(data=ComplaintNoteOut.model_validate(note), meta=request_meta(request))


@router.post("/{complaint_id}/follow-ups", status_code=status.HTTP_201_CREATED)
async def schedule_follow_up(
    complaint_id: uuid.UUID,
    payload: FollowUpCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintFollowUpOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    follow_up = await service.schedule_follow_up(
        session,
        actor=actor,
        complaint=complaint,
        scheduled_at=payload.scheduled_at,
        notes=payload.notes,
    )
    return DataResponse(
        data=ComplaintFollowUpOut.model_validate(follow_up), meta=request_meta(request)
    )


@router.post("/follow-ups/{follow_up_id}/complete")
async def complete_follow_up(
    follow_up_id: uuid.UUID,
    payload: FollowUpCompleteIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintFollowUpOut]:
    follow_up = await _get_follow_up_or_404(session, follow_up_id)
    follow_up = await service.complete_follow_up(
        session,
        actor=actor,
        follow_up=follow_up,
        outcome=payload.outcome,
        notes=payload.notes,
    )
    return DataResponse(
        data=ComplaintFollowUpOut.model_validate(follow_up), meta=request_meta(request)
    )


@router.post("/{complaint_id}/links", status_code=status.HTTP_201_CREATED)
async def link_complaint(
    complaint_id: uuid.UUID,
    payload: ComplaintLinkCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ComplaintLinkOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    try:
        link = await service.link_complaint(
            session,
            actor=actor,
            complaint=complaint,
            related_complaint_id=payload.related_complaint_id,
            relationship_type=payload.relationship_type,
        )
    except ComplaintError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=ComplaintLinkOut.model_validate(link), meta=request_meta(request))


@router.get("/{complaint_id}/timeline")
async def get_complaint_timeline(
    complaint_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("complaints.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TimelineEntryOut]]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    entries = await service.build_timeline(session, complaint_id)
    return DataResponse(data=[TimelineEntryOut(**e) for e in entries], meta=request_meta(request))


@router.get("/{complaint_id}/recovery-actions")
async def list_complaint_recovery_actions(
    complaint_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    actor: StaffUser = Depends(require_permission("recovery.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RecoveryActionOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    rows, total = await recovery_service.list_actions(
        session, page=page, page_size=page_size, complaint_id=complaint_id
    )
    return PaginatedResponse(
        data=[RecoveryActionOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/{complaint_id}/recovery-actions", status_code=status.HTTP_201_CREATED)
async def propose_complaint_recovery_action(
    complaint_id: uuid.UUID,
    payload: RecoveryActionProposeIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("recovery.propose")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecoveryActionOut]:
    complaint = await _get_complaint_or_404(session, complaint_id)
    await _authorize_complaint_access(session, actor=actor, complaint=complaint)
    action = await recovery_service.propose_action(
        session,
        actor=actor,
        complaint=complaint,
        recovery_type=payload.recovery_type,
        value_minor=payload.value_minor,
        points=payload.points,
        description=payload.description,
    )
    return DataResponse(data=RecoveryActionOut.model_validate(action), meta=request_meta(request))
