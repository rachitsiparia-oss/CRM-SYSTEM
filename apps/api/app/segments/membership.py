"""Dynamic evaluation, materialization, and static add/remove for
`segments`/`segment_memberships` — GROWTH_AND_INTELLIGENCE.md section 4.

Dynamic segments are evaluated live for one customer at a time
(`evaluate_for_customer`) via the shared `app.commercial_rules` engine.
`refresh` materializes a dynamic segment's current membership into
`segment_memberships` by walking the active customer base in bounded,
keyset-paginated batches — never loading the whole table into memory at
once (CLAUDE.md section 5.2). At current RKPR scale (single restaurant,
thousands rather than millions of customers) a synchronous, chunked
refresh is an acceptable MVP; if the customer base grows enough for this
to become slow, move the loop into an ARQ job without changing its
per-batch logic.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.commercial_rules.evaluator import evaluate
from app.commercial_rules.facts import resolve_customer_facts
from app.commercial_rules.schema import RuleEvaluationResult, RuleNode
from app.db.models import Customer, Segment, SegmentMembership, StaffUser
from app.segments.errors import WrongSegmentTypeError
from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_REFRESH_BATCH_SIZE = 500
_EXCLUDED_CUSTOMER_STATUSES = ("merged", "archived")
_rule_node_adapter: TypeAdapter[RuleNode] = TypeAdapter(RuleNode)


async def evaluate_for_customer(
    session: AsyncSession, *, segment: Segment, customer_id: uuid.UUID
) -> RuleEvaluationResult:
    if segment.segment_type != "dynamic" or segment.rule_definition is None:
        raise WrongSegmentTypeError(
            f"Segment {segment.code!r} is not a dynamic, rule-bearing segment."
        )
    facts = await resolve_customer_facts(session, customer_id=customer_id)
    node = _rule_node_adapter.validate_python(segment.rule_definition)
    return evaluate(node, facts)


async def _current_member_ids(session: AsyncSession, segment_id: uuid.UUID) -> set[uuid.UUID]:
    latest_membership = (
        select(
            SegmentMembership.customer_id,
            func.max(SegmentMembership.created_at).label("latest_at"),
        )
        .where(SegmentMembership.segment_id == segment_id)
        .group_by(SegmentMembership.customer_id)
        .subquery()
    )
    rows = await session.execute(
        select(SegmentMembership.customer_id)
        .join(
            latest_membership,
            (SegmentMembership.customer_id == latest_membership.c.customer_id)
            & (SegmentMembership.created_at == latest_membership.c.latest_at),
        )
        .where(SegmentMembership.segment_id == segment_id, SegmentMembership.action == "added")
    )
    return {row[0] for row in rows}


async def list_members(
    session: AsyncSession, *, segment_id: uuid.UUID, page: int, page_size: int
) -> tuple[list[uuid.UUID], int]:
    member_ids = sorted(await _current_member_ids(session, segment_id), key=str)
    total = len(member_ids)
    start = (page - 1) * page_size
    return member_ids[start : start + page_size], total


async def add_static_member(
    session: AsyncSession,
    *,
    segment: Segment,
    customer_id: uuid.UUID,
    actor: StaffUser,
    reason: str | None,
) -> SegmentMembership:
    if segment.segment_type != "static":
        raise WrongSegmentTypeError(f"Segment {segment.code!r} is not a static segment.")
    membership = SegmentMembership(
        id=uuid.uuid4(),
        segment_id=segment.id,
        customer_id=customer_id,
        action="added",
        source="manual",
        added_by=actor.id,
        reason=reason,
        created_at=datetime.now(UTC),
    )
    session.add(membership)
    await session.flush()
    return membership


async def remove_static_member(
    session: AsyncSession,
    *,
    segment: Segment,
    customer_id: uuid.UUID,
    actor: StaffUser,
    reason: str | None,
) -> SegmentMembership:
    if segment.segment_type != "static":
        raise WrongSegmentTypeError(f"Segment {segment.code!r} is not a static segment.")
    membership = SegmentMembership(
        id=uuid.uuid4(),
        segment_id=segment.id,
        customer_id=customer_id,
        action="removed",
        source="manual",
        added_by=actor.id,
        reason=reason,
        created_at=datetime.now(UTC),
    )
    session.add(membership)
    await session.flush()
    return membership


async def refresh(session: AsyncSession, *, segment: Segment) -> int:
    """Materializes a dynamic segment's current membership. Returns the
    computed member count. Writes only the delta (added/removed rows) so
    the membership history stays a true record of what changed on this
    refresh, not a full re-add of everyone still eligible."""
    if segment.segment_type != "dynamic" or segment.rule_definition is None:
        raise WrongSegmentTypeError(
            f"Segment {segment.code!r} is not a dynamic, rule-bearing segment."
        )

    node = _rule_node_adapter.validate_python(segment.rule_definition)
    current_members = await _current_member_ids(session, segment.id)
    eligible_now: set[uuid.UUID] = set()

    last_id: uuid.UUID | None = None
    while True:
        query = (
            select(Customer.id)
            .where(
                Customer.deleted_at.is_(None),
                Customer.customer_status.not_in(_EXCLUDED_CUSTOMER_STATUSES),
            )
            .order_by(Customer.id)
            .limit(_REFRESH_BATCH_SIZE)
        )
        if last_id is not None:
            query = query.where(Customer.id > last_id)
        batch = list(await session.scalars(query))
        if not batch:
            break

        for customer_id in batch:
            facts = await resolve_customer_facts(session, customer_id=customer_id)
            result = evaluate(node, facts)
            if result.eligible:
                eligible_now.add(customer_id)

        last_id = batch[-1]
        if len(batch) < _REFRESH_BATCH_SIZE:
            break

    now = datetime.now(UTC)
    to_add = eligible_now - current_members
    to_remove = current_members - eligible_now
    for customer_id in to_add:
        session.add(
            SegmentMembership(
                id=uuid.uuid4(),
                segment_id=segment.id,
                customer_id=customer_id,
                action="added",
                source="refresh",
                added_by=None,
                reason=None,
                created_at=now,
            )
        )
    for customer_id in to_remove:
        session.add(
            SegmentMembership(
                id=uuid.uuid4(),
                segment_id=segment.id,
                customer_id=customer_id,
                action="removed",
                source="refresh",
                added_by=None,
                reason=None,
                created_at=now,
            )
        )

    segment.last_computed_count = len(eligible_now)
    segment.estimated_count = len(eligible_now)
    segment.last_refreshed_at = now
    await session.flush()
    return len(eligible_now)
