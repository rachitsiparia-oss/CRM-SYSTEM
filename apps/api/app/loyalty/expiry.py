"""Loyalty points expiry sweep — GROWTH_AND_INTELLIGENCE.md section 5.4.
`LoyaltyProgram.points_expiry_days` configures how long an earn lot lives,
but nothing before this phase ever called
`post_entry(entry_type="expire", ...)` to actually enforce it. This is the
new engine function Phase 15's scheduler registers — the mechanism
(`post_entry` already fully supports `entry_type="expire"`) existed; the
sweep that calls it did not.

`LoyaltyLedgerEntry.remaining_in_lot` is set once at earn time and is
never decremented by a later redemption — this schema has no FIFO
lot-consumption tracking, a known simplification carried over from Phase
12, not something this phase safely retrofits. To stay correct despite
that gap, this sweep expires `min(remaining_in_lot, account.points_balance)`
rather than `remaining_in_lot` outright, so an account can never be driven
negative or over-expired past what it actually still holds.
"""

from datetime import UTC, datetime

from app.db.models import LoyaltyAccount, LoyaltyLedgerEntry
from app.loyalty.ledger import post_entry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def expire_due_points(session: AsyncSession, *, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    due_entries = (
        await session.scalars(
            select(LoyaltyLedgerEntry).where(
                LoyaltyLedgerEntry.expiry_at.isnot(None),
                LoyaltyLedgerEntry.expiry_at <= now,
                LoyaltyLedgerEntry.remaining_in_lot.isnot(None),
                LoyaltyLedgerEntry.remaining_in_lot > 0,
            )
        )
    ).all()

    expired_count = 0
    for entry in due_entries:
        account = await session.get(LoyaltyAccount, entry.account_id)
        amount = min(entry.remaining_in_lot or 0, account.points_balance if account else 0)
        if amount > 0:
            await post_entry(
                session,
                account_id=entry.account_id,
                entry_type="expire",
                points=amount,
                idempotency_key=f"loyalty-expire:{entry.id}",
                actor_id=None,
                source_type="loyalty_ledger_entry",
                source_id=entry.id,
                description="Automatic points expiry.",
            )
            expired_count += 1
        entry.remaining_in_lot = 0
        await session.flush()
    return expired_count
