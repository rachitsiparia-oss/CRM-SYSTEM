"""Segment configuration CRUD and lifecycle — GROWTH_AND_INTELLIGENCE.md
section 4. Segment rows are mutable configuration; membership history is
the immutable part (see app.segments.membership).
"""

from __future__ import annotations

import uuid

from app.audit.service import record_audit_event
from app.db.models import Segment, StaffUser
from app.segments.errors import (
    DuplicateSegmentCodeError,
    InvalidRuleDefinitionError,
    SegmentError,
)
from app.segments.schemas import SegmentCreateIn, SegmentStatus, SegmentUpdateIn
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_SEGMENT_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active", "archived"},
    "active": {"archived"},
    "archived": set(),
}


async def list_segments(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    segment_type: str | None = None,
) -> tuple[list[Segment], int]:
    query = select(Segment)
    count_query = select(func.count()).select_from(Segment)
    if status is not None:
        query = query.where(Segment.status == status)
        count_query = count_query.where(Segment.status == status)
    if segment_type is not None:
        query = query.where(Segment.segment_type == segment_type)
        count_query = count_query.where(Segment.segment_type == segment_type)

    total = await session.scalar(count_query)
    rows = await session.scalars(
        query.order_by(Segment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rows), total or 0


async def get_segment(session: AsyncSession, segment_id: uuid.UUID) -> Segment | None:
    return await session.get(Segment, segment_id)


async def get_segment_by_code(session: AsyncSession, code: str) -> Segment | None:
    result: Segment | None = await session.scalar(select(Segment).where(Segment.code == code))
    return result


async def create_segment(
    session: AsyncSession, *, actor: StaffUser, payload: SegmentCreateIn
) -> Segment:
    existing = await get_segment_by_code(session, payload.code)
    if existing is not None:
        raise DuplicateSegmentCodeError(f"Segment code {payload.code!r} is already in use.")

    segment = Segment(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        segment_type=payload.segment_type,
        status="draft",
        rule_definition=(
            payload.rule_definition.model_dump(mode="json")
            if payload.rule_definition is not None
            else None
        ),
        rule_version=1,
        refresh_strategy=payload.refresh_strategy,
        owner_staff_id=actor.id,
        is_seed_builtin=False,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(segment)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="segment.created",
        target_type="segment",
        target_id=segment.id,
        safe_metadata={"code": segment.code, "segment_type": segment.segment_type},
    )
    return segment


async def update_segment(
    session: AsyncSession, *, actor: StaffUser, segment: Segment, payload: SegmentUpdateIn
) -> Segment:
    if payload.name is not None:
        segment.name = payload.name
    if payload.description is not None:
        segment.description = payload.description
    if payload.rule_definition is not None:
        if segment.segment_type != "dynamic":
            raise InvalidRuleDefinitionError(
                f"Segment {segment.code!r} is static and cannot carry a rule_definition."
            )
        segment.rule_definition = payload.rule_definition.model_dump(mode="json")
        segment.rule_version += 1
    if payload.refresh_strategy is not None:
        segment.refresh_strategy = payload.refresh_strategy
    segment.updated_by = actor.id
    await session.flush()
    return segment


async def transition_segment(
    session: AsyncSession, *, actor: StaffUser, segment: Segment, target_status: SegmentStatus
) -> Segment:
    allowed = _SEGMENT_TRANSITIONS.get(segment.status, set())
    if target_status not in allowed:
        raise SegmentError(
            f"Cannot transition segment from {segment.status!r} to {target_status!r}."
        )
    segment.status = target_status
    segment.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="segment.transitioned",
        target_type="segment",
        target_id=segment.id,
        safe_metadata={"target_status": target_status},
    )
    return segment
