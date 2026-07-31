"""Idempotent development seed data for Segments — two canonical, staff-
managed dynamic segments other Phase 12 seed data (campaigns) targets.
"""

from __future__ import annotations

from app.commercial_rules.schema import RuleCondition
from app.db.models import StaffUser
from app.segments import service
from app.segments.schemas import SegmentCreateIn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_SEGMENTS: tuple[tuple[str, str, str, str, object], ...] = (
    (
        "vip_customers",
        "VIP Customers",
        "Customers with high lifetime spend.",
        "customer.lifetime_spend_minor",
        500_000,
    ),
    (
        "new_customers",
        "New Customers",
        "Customers who joined in the last 30 days.",
        "customer.days_since_created",
        30,
    ),
)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def seed_segments(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    for code, name, description, fact, threshold in _SEGMENTS:
        existing = await service.get_segment_by_code(session, code)
        if existing is not None:
            continue
        operator = "gte" if fact == "customer.lifetime_spend_minor" else "lte"
        segment = await service.create_segment(
            session,
            actor=actor,
            payload=SegmentCreateIn(
                code=code,
                name=name,
                description=description,
                segment_type="dynamic",
                rule_definition=RuleCondition(fact=fact, operator=operator, value=threshold),  # type: ignore[arg-type]
            ),
        )
        segment.is_seed_builtin = True
        await service.transition_segment(
            session, actor=actor, segment=segment, target_status="active"
        )
