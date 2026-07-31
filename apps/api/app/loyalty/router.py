import uuid

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import LoyaltyAccount, LoyaltyProgram, LoyaltyTier, StaffUser
from app.db.session import get_db
from app.loyalty import accounts, analytics, programs
from app.loyalty.errors import LoyaltyError
from app.loyalty.schemas import (
    AccountOut,
    AdjustIn,
    EarnIn,
    EnrollIn,
    LedgerEntryOut,
    LoyaltyAnalyticsOut,
    ProgramCreateIn,
    ProgramOut,
    ProgramTransitionIn,
    ProgramUpdateIn,
    RedeemIn,
    ReverseIn,
    TierAssignIn,
    TierCreateIn,
    TierOut,
)
from app.permissions.dependencies import require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/loyalty", tags=["loyalty"])


async def _get_program_or_404(session: AsyncSession, program_id: uuid.UUID) -> LoyaltyProgram:
    program = await programs.get_program(session, program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Loyalty program not found.")
    return program


async def _get_account_or_404(session: AsyncSession, account_id: uuid.UUID) -> LoyaltyAccount:
    account = await accounts.get_account(session, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Loyalty account not found.")
    return account


@router.get("/programs")
async def list_programs(
    request: Request,
    _actor: StaffUser = Depends(require_permission("loyalty.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ProgramOut]]:
    rows = await programs.list_programs(session)
    return DataResponse(
        data=[ProgramOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/programs", status_code=status.HTTP_201_CREATED)
async def create_program(
    payload: ProgramCreateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProgramOut]:
    try:
        program = await programs.create_program(session, actor=actor, payload=payload)
    except LoyaltyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=ProgramOut.model_validate(program), meta=request_meta(request))


@router.patch("/programs/{program_id}")
async def update_program(
    program_id: uuid.UUID,
    payload: ProgramUpdateIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProgramOut]:
    program = await _get_program_or_404(session, program_id)
    program = await programs.update_program(session, actor=actor, program=program, payload=payload)
    return DataResponse(data=ProgramOut.model_validate(program), meta=request_meta(request))


@router.post("/programs/{program_id}/transition")
async def transition_program(
    program_id: uuid.UUID,
    payload: ProgramTransitionIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProgramOut]:
    program = await _get_program_or_404(session, program_id)
    try:
        program = await programs.transition_program(
            session, actor=actor, program=program, target_status=payload.target_status
        )
    except LoyaltyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=ProgramOut.model_validate(program), meta=request_meta(request))


@router.get("/tiers")
async def list_tiers(
    request: Request,
    program_id: uuid.UUID = Query(...),
    _actor: StaffUser = Depends(require_permission("loyalty.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TierOut]]:
    rows = await programs.list_tiers(session, program_id)
    return DataResponse(data=[TierOut.model_validate(r) for r in rows], meta=request_meta(request))


@router.post("/tiers", status_code=status.HTTP_201_CREATED)
async def create_tier(
    payload: TierCreateIn,
    request: Request,
    program_id: uuid.UUID = Query(...),
    actor: StaffUser = Depends(require_permission("loyalty.tiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TierOut]:
    program = await _get_program_or_404(session, program_id)
    tier = await programs.create_tier(session, actor=actor, program=program, payload=payload)
    return DataResponse(data=TierOut.model_validate(tier), meta=request_meta(request))


@router.get("/accounts")
async def get_account_for_customer(
    request: Request,
    customer_id: uuid.UUID = Query(...),
    program_id: uuid.UUID | None = Query(default=None),
    _actor: StaffUser = Depends(require_permission("loyalty.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AccountOut | None]:
    account = await accounts.get_account_for_customer(
        session, customer_id=customer_id, program_id=program_id
    )
    return DataResponse(
        data=AccountOut.model_validate(account) if account else None, meta=request_meta(request)
    )


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def enroll(
    payload: EnrollIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AccountOut]:
    try:
        account = await accounts.enroll(session, actor=actor, payload=payload)
    except LoyaltyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=AccountOut.model_validate(account), meta=request_meta(request))


@router.get("/accounts/{account_id}/ledger")
async def list_ledger(
    account_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("loyalty.view")),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[LedgerEntryOut]:
    await _get_account_or_404(session, account_id)
    rows, total = await accounts.list_ledger(
        session, account_id=account_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        data=[LedgerEntryOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page, page_size=page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/earn", status_code=status.HTTP_201_CREATED)
async def earn(
    payload: EarnIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await accounts.earn(session, actor=actor, payload=payload)
    except LoyaltyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/redeem", status_code=status.HTTP_201_CREATED)
async def redeem(
    payload: RedeemIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await accounts.redeem(session, actor=actor, payload=payload)
    except LoyaltyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/adjust", status_code=status.HTTP_201_CREATED)
async def adjust(
    payload: AdjustIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await accounts.adjust(session, actor=actor, payload=payload)
    except LoyaltyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/reverse", status_code=status.HTTP_201_CREATED)
async def reverse(
    payload: ReverseIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.reverse")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await accounts.reverse(session, actor=actor, payload=payload)
    except LoyaltyError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/accounts/{account_id}/tier")
async def assign_tier(
    account_id: uuid.UUID,
    payload: TierAssignIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("loyalty.tiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AccountOut]:
    account = await _get_account_or_404(session, account_id)
    tier = await session.get(LoyaltyTier, payload.tier_id)
    if tier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Loyalty tier not found.")
    await accounts.assign_tier(
        session, actor=actor, account=account, tier=tier, reason=payload.reason
    )
    return DataResponse(data=AccountOut.model_validate(account), meta=request_meta(request))


@router.get("/analytics")
async def get_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("loyalty.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LoyaltyAnalyticsOut]:
    result = await analytics.get_analytics(session)
    return DataResponse(data=result, meta=request_meta(request))
