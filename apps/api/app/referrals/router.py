import uuid

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import ReferralCode, ReferralProgram, ReferralRelationship, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.referrals import relationships, service
from app.referrals.errors import ReferralError
from app.referrals.schemas import (
    AttributeReferralIn,
    CodeOut,
    IssueCodeIn,
    ProgramCreateIn,
    ProgramOut,
    ProgramTransitionIn,
    ProgramUpdateIn,
    QualifyReferralIn,
    RejectReferralIn,
    RelationshipOut,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/referrals", tags=["referrals"])


async def _get_program_or_404(session: AsyncSession, program_id: uuid.UUID) -> ReferralProgram:
    program = await service.get_program(session, program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Referral program not found.")
    return program


async def _get_code_or_404(session: AsyncSession, code_value: str) -> ReferralCode:
    code = await service.get_code_by_value(session, code_value)
    if code is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Referral code not found.")
    return code


async def _get_relationship_or_404(
    session: AsyncSession, relationship_id: uuid.UUID
) -> ReferralRelationship:
    relationship = await relationships.get_relationship(session, relationship_id)
    if relationship is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Referral relationship not found.")
    return relationship


@router.get("/programs")
async def list_programs(
    request: Request,
    _actor: StaffUser = Depends(require_permission("referrals.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ProgramOut]]:
    rows = await service.list_programs(session)
    return DataResponse(
        data=[ProgramOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/programs", status_code=status.HTTP_201_CREATED)
async def create_program(
    payload: ProgramCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("referrals.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProgramOut]:
    try:
        program = await service.create_program(session, actor=actor, payload=payload)
    except ReferralError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=ProgramOut.model_validate(program), meta=request_meta(request))


@router.patch("/programs/{program_id}")
async def update_program(
    program_id: uuid.UUID,
    payload: ProgramUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("referrals.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProgramOut]:
    program = await _get_program_or_404(session, program_id)
    program = await service.update_program(session, actor=actor, program=program, payload=payload)
    return DataResponse(data=ProgramOut.model_validate(program), meta=request_meta(request))


@router.post("/programs/{program_id}/transition")
async def transition_program(
    program_id: uuid.UUID,
    payload: ProgramTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("referrals.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProgramOut]:
    program = await _get_program_or_404(session, program_id)
    try:
        program = await service.transition_program(
            session, actor=actor, program=program, target_status=payload.target_status
        )
    except ReferralError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=ProgramOut.model_validate(program), meta=request_meta(request))


@router.post("/programs/{program_id}/codes", status_code=status.HTTP_201_CREATED)
async def issue_code(
    program_id: uuid.UUID,
    payload: IssueCodeIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("referrals.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CodeOut]:
    program = await _get_program_or_404(session, program_id)
    try:
        code = await service.issue_code(
            session,
            actor=actor,
            program=program,
            referrer_customer_id=payload.referrer_customer_id,
            expires_at=payload.expires_at,
        )
    except ReferralError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=CodeOut.model_validate(code), meta=request_meta(request))


@router.get("/codes/{code_value}")
async def get_code(
    code_value: str,
    request: Request,
    _actor: StaffUser = Depends(require_permission("referrals.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CodeOut]:
    code = await _get_code_or_404(session, code_value)
    return DataResponse(data=CodeOut.model_validate(code), meta=request_meta(request))


@router.get("/relationships")
async def list_relationships(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    program_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    _actor: StaffUser = Depends(require_permission("referrals.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RelationshipOut]:
    rows, total = await relationships.list_relationships(
        session, page=page, page_size=page_size, program_id=program_id, status=status_filter
    )
    return PaginatedResponse(
        data=[RelationshipOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/relationships/attribute", status_code=status.HTTP_201_CREATED)
async def attribute_referral(
    payload: AttributeReferralIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("referrals.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RelationshipOut]:
    code = await _get_code_or_404(session, payload.code)
    try:
        relationship = await relationships.attribute(
            session,
            actor=actor,
            code=code,
            referred_contact=payload.referred_contact,
            referred_customer_id=payload.referred_customer_id,
        )
    except ReferralError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=RelationshipOut.model_validate(relationship), meta=request_meta(request)
    )


@router.post("/relationships/{relationship_id}/qualify")
async def qualify_referral(
    relationship_id: uuid.UUID,
    payload: QualifyReferralIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("referrals.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RelationshipOut]:
    relationship = await _get_relationship_or_404(session, relationship_id)
    try:
        relationship = await relationships.qualify(
            session,
            actor=actor,
            relationship=relationship,
            qualifying_order_id=payload.qualifying_order_id,
        )
    except ReferralError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=RelationshipOut.model_validate(relationship), meta=request_meta(request)
    )


@router.post("/relationships/{relationship_id}/reject")
async def reject_referral(
    relationship_id: uuid.UUID,
    payload: RejectReferralIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("referrals.review")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RelationshipOut]:
    relationship = await _get_relationship_or_404(session, relationship_id)
    try:
        relationship = await relationships.reject(
            session, actor=actor, relationship=relationship, reason=payload.reason
        )
    except ReferralError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=RelationshipOut.model_validate(relationship), meta=request_meta(request)
    )


@router.post("/relationships/{relationship_id}/reward")
async def reward_referral(
    relationship_id: uuid.UUID,
    request: Request,
    actor: StaffUser = Depends(require_permission("referrals.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RelationshipOut]:
    relationship = await _get_relationship_or_404(session, relationship_id)
    try:
        relationship = await relationships.reward(session, actor=actor, relationship=relationship)
    except ReferralError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(
        data=RelationshipOut.model_validate(relationship), meta=request_meta(request)
    )
