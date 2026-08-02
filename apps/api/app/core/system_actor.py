"""The staff user attributed to a system-triggered (scheduled/automated)
action that a service function's signature requires a real `actor:
StaffUser` for — the same `_system_actor` helper duplicated across
`app.achievements.seed`, `app.campaigns.seed`, `app.communications.seed`,
`app.complaints.seed`, and others, consolidated here for Phase 15's new
scheduled engine functions rather than adding a sixth copy. Returns `None`
(never raises) when no privileged staff account exists yet — CLAUDE.md
section 21's "optional/unconfigured dependencies fail clearly only when
used"; a caller with no system actor available should skip its work for
this tick, not crash the scheduler.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StaffUser


async def get_system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result
