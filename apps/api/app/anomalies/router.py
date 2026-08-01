"""Anomaly API — GROWTH_AND_INTELLIGENCE.md section 15.7. `/evaluate` is
the deterministic engine's manual trigger until Phase 15 wires a live
schedule (CLAUDE.md section 9's "engine, not scheduler" split)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.anomalies import service
from app.anomalies.engine import evaluate_all_active_rules
from app.anomalies.errors import AnomalyError
from app.anomalies.schemas import (
    AnomalyFindingOut,
    AnomalyFindingTransitionIn,
    AnomalyRuleCreateIn,
    AnomalyRuleOut,
    AnomalyRuleUpdateIn,
)
from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import AnomalyFinding, AnomalyRule, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/anomalies", tags=["anomalies"])


async def _get_rule_or_404(session: AsyncSession, rule_id: uuid.UUID) -> AnomalyRule:
    rule = await service.get_rule(session, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Anomaly rule not found.")
    return rule


async def _get_finding_or_404(session: AsyncSession, finding_id: uuid.UUID) -> AnomalyFinding:
    finding = await service.get_finding(session, finding_id)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Anomaly finding not found.")
    return finding


@router.get("/rules")
async def list_rules(
    request: Request,
    is_active: bool | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("anomalies.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[AnomalyRuleOut]]:
    rows = await service.list_rules(session, is_active=is_active)
    return DataResponse(
        data=[AnomalyRuleOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: AnomalyRuleCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("anomalies.manage_rules")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AnomalyRuleOut]:
    try:
        rule = await service.create_rule(session, actor=actor, payload=payload)
    except AnomalyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=AnomalyRuleOut.model_validate(rule), meta=request_meta(request))


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: uuid.UUID,
    payload: AnomalyRuleUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("anomalies.manage_rules")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AnomalyRuleOut]:
    rule = await _get_rule_or_404(session, rule_id)
    rule = await service.update_rule(session, actor=actor, rule=rule, payload=payload)
    return DataResponse(data=AnomalyRuleOut.model_validate(rule), meta=request_meta(request))


@router.post("/evaluate")
async def evaluate_rules(
    request: Request,
    _actor: StaffUser = Depends(require_permission("anomalies.manage_rules")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[AnomalyFindingOut]]:
    findings = await evaluate_all_active_rules(session)
    return DataResponse(
        data=[AnomalyFindingOut.model_validate(f) for f in findings], meta=request_meta(request)
    )


@router.get("/findings")
async def list_findings(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("anomalies.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AnomalyFindingOut]:
    rows, total = await service.list_findings(
        session, status_filter=status_filter, severity=severity, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=[AnomalyFindingOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/findings/{finding_id}")
async def get_finding(
    finding_id: uuid.UUID,
    request: Request,
    _actor: StaffUser = Depends(require_permission("anomalies.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AnomalyFindingOut]:
    finding = await _get_finding_or_404(session, finding_id)
    return DataResponse(data=AnomalyFindingOut.model_validate(finding), meta=request_meta(request))


@router.post("/findings/{finding_id}/transition")
async def transition_finding(
    finding_id: uuid.UUID,
    payload: AnomalyFindingTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("anomalies.acknowledge")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AnomalyFindingOut]:
    finding = await _get_finding_or_404(session, finding_id)
    try:
        finding = await service.transition_finding(
            session,
            actor=actor,
            finding=finding,
            target_status=payload.target_status,
            resolution_note=payload.resolution_note,
        )
    except AnomalyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=AnomalyFindingOut.model_validate(finding), meta=request_meta(request))
