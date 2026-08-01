"""Service-recovery action and compensation-approval-rule API —
GROWTH_AND_INTELLIGENCE.md section 12.6. Action *proposal* is nested under
`app.complaints.router` (`POST /complaints/{id}/recovery-actions`) since it
always originates from a specific complaint; everything else that operates
on an already-identified action lives here to avoid route-shadowing."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import CompensationApprovalRule, ServiceRecoveryAction, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.service_recovery import analytics, service
from app.service_recovery.errors import ServiceRecoveryError
from app.service_recovery.schemas import (
    ActionHistoryOut,
    ApprovalRuleCreateIn,
    ApprovalRuleOut,
    ApprovalRuleUpdateIn,
    RecoveryActionOut,
    RecoveryActionRejectIn,
    RecoveryActionReverseIn,
    RecoveryAnalyticsOut,
)

router = APIRouter(prefix="/api/v1/service-recovery", tags=["service-recovery"])


async def _get_action_or_404(session: AsyncSession, action_id: uuid.UUID) -> ServiceRecoveryAction:
    action = await service.get_action(session, action_id)
    if action is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Recovery action not found.")
    return action


async def _get_rule_or_404(session: AsyncSession, rule_id: uuid.UUID) -> CompensationApprovalRule:
    rule = await service.get_approval_rule(session, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Approval rule not found.")
    return rule


@router.get("/actions")
async def list_recovery_actions(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    complaint_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    recovery_type: str | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("recovery.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RecoveryActionOut]:
    rows, total = await service.list_actions(
        session,
        page=page,
        page_size=page_size,
        complaint_id=complaint_id,
        customer_id=customer_id,
        status=status_filter,
        recovery_type=recovery_type,
    )
    return PaginatedResponse(
        data=[RecoveryActionOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/analytics")
async def get_recovery_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("recovery.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecoveryAnalyticsOut]:
    result = await analytics.get_analytics(session)
    return DataResponse(data=result, meta=request_meta(request))


@router.get("/approval-rules")
async def list_approval_rules(
    request: Request,
    is_active: bool | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("recovery.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ApprovalRuleOut]]:
    rows = await service.list_approval_rules(session, is_active=is_active)
    return DataResponse(
        data=[ApprovalRuleOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/approval-rules", status_code=status.HTTP_201_CREATED)
async def create_approval_rule(
    payload: ApprovalRuleCreateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("recovery.rules.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ApprovalRuleOut]:
    rule = await service.create_approval_rule(session, payload=payload)
    return DataResponse(data=ApprovalRuleOut.model_validate(rule), meta=request_meta(request))


@router.patch("/approval-rules/{rule_id}")
async def update_approval_rule(
    rule_id: uuid.UUID,
    payload: ApprovalRuleUpdateIn,
    request: Request,
    _actor: StaffUser = Depends(require_permission("recovery.rules.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ApprovalRuleOut]:
    rule = await _get_rule_or_404(session, rule_id)
    rule = await service.update_approval_rule(session, rule=rule, payload=payload)
    return DataResponse(data=ApprovalRuleOut.model_validate(rule), meta=request_meta(request))


@router.get("/actions/{action_id}")
async def get_recovery_action(
    action_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("recovery.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecoveryActionOut]:
    action = await _get_action_or_404(session, action_id)
    return DataResponse(data=RecoveryActionOut.model_validate(action), meta=request_meta(request))


@router.get("/actions/{action_id}/history")
async def list_recovery_action_history(
    action_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("recovery.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ActionHistoryOut]]:
    await _get_action_or_404(session, action_id)
    rows = await service.list_action_history(session, action_id)
    return DataResponse(
        data=[ActionHistoryOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/actions/{action_id}/approve")
async def approve_recovery_action(
    action_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("recovery.approve")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecoveryActionOut]:
    action = await _get_action_or_404(session, action_id)
    try:
        action = await service.approve_action(session, actor=actor, action=action)
    except ServiceRecoveryError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=RecoveryActionOut.model_validate(action), meta=request_meta(request))


@router.post("/actions/{action_id}/reject")
async def reject_recovery_action(
    action_id: uuid.UUID,
    payload: RecoveryActionRejectIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("recovery.reject")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecoveryActionOut]:
    action = await _get_action_or_404(session, action_id)
    try:
        action = await service.reject_action(
            session, actor=actor, action=action, reason=payload.reason
        )
    except ServiceRecoveryError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=RecoveryActionOut.model_validate(action), meta=request_meta(request))


@router.post("/actions/{action_id}/execute")
async def execute_recovery_action(
    action_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("recovery.execute")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecoveryActionOut]:
    action = await _get_action_or_404(session, action_id)
    try:
        action = await service.execute_action(session, actor=actor, action=action)
    except ServiceRecoveryError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=RecoveryActionOut.model_validate(action), meta=request_meta(request))


@router.post("/actions/{action_id}/reverse")
async def reverse_recovery_action(
    action_id: uuid.UUID,
    payload: RecoveryActionReverseIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("recovery.reverse")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecoveryActionOut]:
    action = await _get_action_or_404(session, action_id)
    try:
        action = await service.reverse_action(
            session, actor=actor, action=action, reason=payload.reason
        )
    except ServiceRecoveryError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=RecoveryActionOut.model_validate(action), meta=request_meta(request))
