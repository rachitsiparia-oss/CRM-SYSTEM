from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics_core.windows import ResolvedWindow
from app.db.models import Campaign, CampaignRecipient, LoyaltyAccount, LoyaltyLedgerEntry

_REDEEM_ENTRY_TYPES = ("redeem_order", "redeem_reward")


async def active_campaigns(session: AsyncSession, window: ResolvedWindow) -> int:
    """Point-in-time gauge as of the window's end boundary."""
    value = await session.scalar(
        select(func.count())
        .select_from(Campaign)
        .where(Campaign.status.in_(("running", "scheduled")), Campaign.created_at < window.end)
    )
    return int(value or 0)


async def delivered_messages(session: AsyncSession, window: ResolvedWindow) -> int:
    """Recipients actually confirmed delivered within the window — never
    a fabricated "attributed revenue" figure without a verified
    attribution model (this phase's own scoping note)."""
    value = await session.scalar(
        select(func.count())
        .select_from(CampaignRecipient)
        .where(
            CampaignRecipient.delivered_at.is_not(None),
            CampaignRecipient.delivered_at >= window.start,
            CampaignRecipient.delivered_at < window.end,
        )
    )
    return int(value or 0)


async def loyalty_members(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(LoyaltyAccount)
        .where(LoyaltyAccount.status == "active", LoyaltyAccount.created_at < window.end)
    )
    return int(value or 0)


async def loyalty_points_redeemed(session: AsyncSession, window: ResolvedWindow) -> int:
    value = await session.scalar(
        select(func.coalesce(func.sum(-LoyaltyLedgerEntry.points_delta), 0)).where(
            LoyaltyLedgerEntry.entry_type.in_(_REDEEM_ENTRY_TYPES),
            LoyaltyLedgerEntry.created_at >= window.start,
            LoyaltyLedgerEntry.created_at < window.end,
        )
    )
    return int(value or 0)
