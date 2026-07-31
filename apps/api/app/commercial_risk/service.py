"""Commercial-risk flag queue — a lightweight, auditable review queue,
not an enterprise fraud platform (this phase's own scope boundary; see
`CommercialRiskFlag`'s docstring). `raise_flag` is the single entry
point other domains call to record a flag; this module never blocks the
triggering action itself — flags are reviewed asynchronously by staff.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.audit.service import record_audit_event
from app.commercial_risk.errors import InvalidStatusTransitionError
from app.commercial_risk.schemas import FlagStatus, FlagType
from app.db.models import CommercialRiskFlag, StaffUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_FLAG_TRANSITIONS: dict[str, set[str]] = {
    "open": {"reviewing", "resolved", "dismissed"},
    "reviewing": {"resolved", "dismissed"},
    "resolved": set(),
    "dismissed": set(),
}


async def list_flags(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    flag_type: str | None = None,
    customer_id: uuid.UUID | None = None,
) -> tuple[list[CommercialRiskFlag], int]:
    query = select(CommercialRiskFlag)
    count_query = select(func.count()).select_from(CommercialRiskFlag)
    if status is not None:
        query = query.where(CommercialRiskFlag.status == status)
        count_query = count_query.where(CommercialRiskFlag.status == status)
    if flag_type is not None:
        query = query.where(CommercialRiskFlag.flag_type == flag_type)
        count_query = count_query.where(CommercialRiskFlag.flag_type == flag_type)
    if customer_id is not None:
        query = query.where(CommercialRiskFlag.customer_id == customer_id)
        count_query = count_query.where(CommercialRiskFlag.customer_id == customer_id)

    total = await session.scalar(count_query)
    rows = await session.scalars(
        query.order_by(CommercialRiskFlag.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def get_flag(session: AsyncSession, flag_id: uuid.UUID) -> CommercialRiskFlag | None:
    return await session.get(CommercialRiskFlag, flag_id)


async def raise_flag(
    session: AsyncSession,
    *,
    flag_type: FlagType,
    summary: str,
    customer_id: uuid.UUID | None = None,
    staff_user_id: uuid.UUID | None = None,
    related_type: str | None = None,
    related_id: uuid.UUID | None = None,
    detail: dict[str, object] | None = None,
) -> CommercialRiskFlag:
    flag = CommercialRiskFlag(
        id=uuid.uuid4(),
        flag_type=flag_type,
        status="open",
        customer_id=customer_id,
        staff_user_id=staff_user_id,
        related_type=related_type,
        related_id=related_id,
        summary=summary,
        detail=detail,
    )
    session.add(flag)
    await session.flush()
    return flag


async def review_flag(
    session: AsyncSession,
    *,
    actor: StaffUser,
    flag: CommercialRiskFlag,
    target_status: FlagStatus,
    resolution_note: str | None,
) -> CommercialRiskFlag:
    allowed = _FLAG_TRANSITIONS.get(flag.status, set())
    if target_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition commercial-risk flag from {flag.status!r} to {target_status!r}."
        )
    flag.status = target_status
    flag.reviewed_by = actor.id
    flag.reviewed_at = datetime.now(UTC)
    if resolution_note is not None:
        flag.resolution_note = resolution_note
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="commercial_risk.flag_reviewed",
        target_type="commercial_risk_flag",
        target_id=flag.id,
        safe_metadata={"target_status": target_status},
    )
    return flag
