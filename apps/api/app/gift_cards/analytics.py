from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.db.models import GiftCard, GiftCardLedgerEntry
from app.gift_cards.schemas import GiftCardAnalyticsOut
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_ACTIVE_STATUSES = ("active", "partially_redeemed")


async def get_analytics(session: AsyncSession) -> GiftCardAnalyticsOut:
    active_cards = await session.scalar(
        select(func.count()).select_from(GiftCard).where(GiftCard.status.in_(_ACTIVE_STATUSES))
    )
    outstanding = await session.scalar(
        select(func.coalesce(func.sum(GiftCard.current_balance_minor), 0)).where(
            GiftCard.status.in_(_ACTIVE_STATUSES)
        )
    )

    since = datetime.now(UTC) - timedelta(days=30)
    issued = await session.scalar(
        select(func.coalesce(func.sum(GiftCardLedgerEntry.amount_delta_minor), 0)).where(
            GiftCardLedgerEntry.entry_type == "issue",
            GiftCardLedgerEntry.created_at >= since,
        )
    )
    redeemed = await session.scalar(
        select(func.coalesce(func.sum(-GiftCardLedgerEntry.amount_delta_minor), 0)).where(
            GiftCardLedgerEntry.entry_type == "redeem",
            GiftCardLedgerEntry.created_at >= since,
        )
    )

    return GiftCardAnalyticsOut(
        active_cards=int(active_cards or 0),
        outstanding_liability_minor=int(outstanding or 0),
        issued_30d_minor=int(issued or 0),
        redeemed_30d_minor=int(redeemed or 0),
    )
