"""GROWTH_AND_INTELLIGENCE.md section 5.11's loyalty reporting list,
scoped to what's derivable from the existing ledger/account schema
without inventing a financial-liability methodology this phase's
instruction doesn't specify.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.db.models import LoyaltyAccount, LoyaltyLedgerEntry, LoyaltyProgram, LoyaltyTier
from app.db.models.loyalty_ledger_entry import EARN_ENTRY_TYPES, REDEEM_ENTRY_TYPES
from app.loyalty.schemas import LoyaltyAnalyticsOut
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_analytics(session: AsyncSession) -> LoyaltyAnalyticsOut:
    active_members = await session.scalar(
        select(func.count()).select_from(LoyaltyAccount).where(LoyaltyAccount.status == "active")
    )

    since = datetime.now(UTC) - timedelta(days=30)
    issued = await session.scalar(
        select(func.coalesce(func.sum(LoyaltyLedgerEntry.points_delta), 0)).where(
            LoyaltyLedgerEntry.entry_type.in_(EARN_ENTRY_TYPES),
            LoyaltyLedgerEntry.created_at >= since,
        )
    )
    redeemed = await session.scalar(
        select(func.coalesce(func.sum(-LoyaltyLedgerEntry.points_delta), 0)).where(
            LoyaltyLedgerEntry.entry_type.in_(REDEEM_ENTRY_TYPES),
            LoyaltyLedgerEntry.created_at >= since,
        )
    )
    expired = await session.scalar(
        select(func.coalesce(func.sum(-LoyaltyLedgerEntry.points_delta), 0)).where(
            LoyaltyLedgerEntry.entry_type == "expire",
            LoyaltyLedgerEntry.created_at >= since,
        )
    )

    outstanding_points = await session.scalar(
        select(func.coalesce(func.sum(LoyaltyAccount.points_balance), 0))
    )
    program = await session.scalar(
        select(LoyaltyProgram).where(LoyaltyProgram.is_default.is_(True))
    )
    liability_minor = 0
    if program is not None and outstanding_points:
        liability_minor = int(
            (outstanding_points / program.redemption_points_per_unit)
            * program.redemption_value_minor
        )

    issued_val = int(issued or 0)
    redeemed_val = int(redeemed or 0)
    redemption_rate = (
        Decimal(redeemed_val) / Decimal(issued_val) * 100 if issued_val > 0 else Decimal(0)
    )

    tier_rows = await session.execute(
        select(LoyaltyTier.name, func.count(LoyaltyAccount.id))
        .join(LoyaltyAccount, LoyaltyAccount.current_tier_id == LoyaltyTier.id)
        .group_by(LoyaltyTier.name)
    )
    tier_distribution = [{"tier": name, "count": count} for name, count in tier_rows]

    return LoyaltyAnalyticsOut(
        active_members=int(active_members or 0),
        points_issued_30d=issued_val,
        points_redeemed_30d=redeemed_val,
        points_expired_30d=int(expired or 0),
        outstanding_points_liability_minor=liability_minor,
        redemption_rate_pct=redemption_rate.quantize(Decimal("0.01")),
        tier_distribution=tier_distribution,
    )
