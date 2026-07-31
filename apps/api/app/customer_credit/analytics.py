from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.customer_credit.schemas import CreditAnalyticsOut
from app.db.models import CustomerCreditAccount, CustomerCreditLedgerEntry
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_analytics(session: AsyncSession) -> CreditAnalyticsOut:
    active_accounts = await session.scalar(
        select(func.count())
        .select_from(CustomerCreditAccount)
        .where(CustomerCreditAccount.status == "active")
    )
    outstanding = await session.scalar(
        select(func.coalesce(func.sum(CustomerCreditAccount.current_balance_minor), 0))
    )

    since = datetime.now(UTC) - timedelta(days=30)
    issued = await session.scalar(
        select(func.coalesce(func.sum(CustomerCreditLedgerEntry.amount_delta_minor), 0)).where(
            CustomerCreditLedgerEntry.entry_type == "issue",
            CustomerCreditLedgerEntry.created_at >= since,
        )
    )
    redeemed = await session.scalar(
        select(func.coalesce(func.sum(-CustomerCreditLedgerEntry.amount_delta_minor), 0)).where(
            CustomerCreditLedgerEntry.entry_type == "redeem",
            CustomerCreditLedgerEntry.created_at >= since,
        )
    )

    return CreditAnalyticsOut(
        active_accounts=int(active_accounts or 0),
        outstanding_liability_minor=int(outstanding or 0),
        issued_30d_minor=int(issued or 0),
        redeemed_30d_minor=int(redeemed or 0),
    )
