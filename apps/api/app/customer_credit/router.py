import uuid

from app.core.pagination import PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.customer_credit import accounts, analytics
from app.customer_credit.errors import CustomerCreditError
from app.customer_credit.schemas import (
    AccountOut,
    AdjustIn,
    CreditAnalyticsOut,
    EnsureAccountIn,
    IssueIn,
    LedgerEntryOut,
    RedeemIn,
    ReverseIn,
)
from app.db.models import CustomerCreditAccount, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/customer-credit", tags=["customer-credit"])


async def _get_account_or_404(
    session: AsyncSession, account_id: uuid.UUID
) -> CustomerCreditAccount:
    account = await accounts.get_account(session, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer credit account not found.")
    return account


@router.get("/accounts")
async def get_account_for_customer(
    request: Request,
    customer_id: uuid.UUID = Query(...),
    _actor: StaffUser = Depends(require_permission("customer_credit.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AccountOut | None]:
    account = await accounts.get_account_for_customer(session, customer_id)
    return DataResponse(
        data=AccountOut.model_validate(account) if account else None, meta=request_meta(request)
    )


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def ensure_account(
    payload: EnsureAccountIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("customer_credit.issue")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AccountOut]:
    account = await accounts.ensure_account(session, actor=actor, payload=payload)
    return DataResponse(data=AccountOut.model_validate(account), meta=request_meta(request))


@router.get("/accounts/{account_id}/ledger")
async def list_ledger(
    account_id: uuid.UUID,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _actor: StaffUser = Depends(require_permission("customer_credit.view")),
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


@router.post("/issue", status_code=status.HTTP_201_CREATED)
async def issue(
    payload: IssueIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("customer_credit.issue")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await accounts.issue(session, actor=actor, payload=payload)
    except CustomerCreditError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/redeem", status_code=status.HTTP_201_CREATED)
async def redeem(
    payload: RedeemIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("customer_credit.issue")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await accounts.redeem(session, actor=actor, payload=payload)
    except CustomerCreditError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/adjust", status_code=status.HTTP_201_CREATED)
async def adjust(
    payload: AdjustIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("customer_credit.adjust")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await accounts.adjust(session, actor=actor, payload=payload)
    except CustomerCreditError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.post("/reverse", status_code=status.HTTP_201_CREATED)
async def reverse(
    payload: ReverseIn,
    request: Request,
    actor: StaffUser = Depends(require_permission("customer_credit.reverse")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[LedgerEntryOut]:
    try:
        entry = await accounts.reverse(session, actor=actor, payload=payload)
    except CustomerCreditError as exc:
        raise HTTPException(exc.status_code, detail=exc.message) from exc
    return DataResponse(data=LedgerEntryOut.model_validate(entry), meta=request_meta(request))


@router.get("/analytics")
async def get_analytics(
    request: Request,
    _actor: StaffUser = Depends(require_permission("customer_credit.analytics.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CreditAnalyticsOut]:
    result = await analytics.get_analytics(session)
    return DataResponse(data=result, meta=request_meta(request))
