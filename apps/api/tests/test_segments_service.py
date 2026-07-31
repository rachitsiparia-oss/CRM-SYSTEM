"""Real-DB tests for `app.segments.service` and `app.segments.membership` —
segment CRUD/validation, the draft->active->archived status state machine,
immutable static-membership history, and dynamic-segment `refresh` against
real `Customer` rows.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.commercial_rules.schema import RuleCondition
from app.db.models import Customer, Segment, StaffUser
from app.segments import membership, service
from app.segments.errors import SegmentError, WrongSegmentTypeError
from app.segments.schemas import SegmentCreateIn, SegmentType
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

# Not `pytestmark = pytest.mark.asyncio` at module scope: this file mixes
# sync `SegmentCreateIn` validation tests with async DB tests, and
# `asyncio_mode = "auto"` (pyproject.toml) already detects async def tests
# without it — applying the mark to the sync tests as well only produces a
# spurious PytestWarning.

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _customer_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": "Test Customer",
        "first_name": "Test",
        "last_name": "Customer",
    }
    base.update(overrides)
    return base


async def _make_customer(session: AsyncSession, **overrides: object) -> Customer:
    customer = Customer(**_customer_kwargs(**overrides))
    session.add(customer)
    await session.flush()
    return customer


def _segment_code() -> str:
    return f"seg-{uuid.uuid4().hex[:10]}"


_ALWAYS_TRUE_RULE = RuleCondition(fact="customer.completed_order_count", operator="gte", value=0)


# --- SegmentCreateIn validation: dynamic requires rule, static forbids it ----


def test_dynamic_segment_requires_rule_definition() -> None:
    with pytest.raises(ValidationError, match="requires a rule_definition"):
        SegmentCreateIn(code=_segment_code(), name="Dynamic", segment_type="dynamic")


def test_static_segment_must_not_have_rule_definition() -> None:
    with pytest.raises(ValidationError, match="must not have a rule_definition"):
        SegmentCreateIn(
            code=_segment_code(),
            name="Static",
            segment_type="static",
            rule_definition=_ALWAYS_TRUE_RULE,
        )


async def test_create_dynamic_segment_succeeds_with_rule(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    payload = SegmentCreateIn(
        code=_segment_code(),
        name="Dynamic",
        segment_type="dynamic",
        rule_definition=_ALWAYS_TRUE_RULE,
    )
    segment = await service.create_segment(db_session, actor=actor, payload=payload)
    assert segment.segment_type == "dynamic"
    assert segment.rule_definition is not None
    assert segment.status == "draft"
    assert segment.rule_version == 1


async def test_create_static_segment_succeeds_without_rule(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    payload = SegmentCreateIn(code=_segment_code(), name="Static", segment_type="static")
    segment = await service.create_segment(db_session, actor=actor, payload=payload)
    assert segment.segment_type == "static"
    assert segment.rule_definition is None


async def test_create_segment_rejects_duplicate_code(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    code = _segment_code()
    await service.create_segment(
        db_session, actor=actor, payload=SegmentCreateIn(code=code, name="A", segment_type="static")
    )
    with pytest.raises(SegmentError):
        await service.create_segment(
            db_session,
            actor=actor,
            payload=SegmentCreateIn(code=code, name="B", segment_type="static"),
        )


# --- Status state machine -----------------------------------------------------


async def _make_segment(
    session: AsyncSession, *, actor: StaffUser, segment_type: SegmentType = "static"
) -> Segment:
    payload = SegmentCreateIn(
        code=_segment_code(),
        name="Segment",
        segment_type=segment_type,
        rule_definition=_ALWAYS_TRUE_RULE if segment_type == "dynamic" else None,
    )
    return await service.create_segment(session, actor=actor, payload=payload)


async def test_draft_to_active_transition_succeeds(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    segment = await _make_segment(db_session, actor=actor)
    updated = await service.transition_segment(
        db_session, actor=actor, segment=segment, target_status="active"
    )
    assert updated.status == "active"


async def test_active_to_archived_transition_succeeds(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    segment = await _make_segment(db_session, actor=actor)
    await service.transition_segment(
        db_session, actor=actor, segment=segment, target_status="active"
    )
    updated = await service.transition_segment(
        db_session, actor=actor, segment=segment, target_status="archived"
    )
    assert updated.status == "archived"


async def test_draft_to_archived_transition_succeeds(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    segment = await _make_segment(db_session, actor=actor)
    updated = await service.transition_segment(
        db_session, actor=actor, segment=segment, target_status="archived"
    )
    assert updated.status == "archived"


async def test_archived_to_active_transition_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    segment = await _make_segment(db_session, actor=actor)
    await service.transition_segment(
        db_session, actor=actor, segment=segment, target_status="archived"
    )
    with pytest.raises(SegmentError):
        await service.transition_segment(
            db_session, actor=actor, segment=segment, target_status="active"
        )


async def test_active_to_draft_transition_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    segment = await _make_segment(db_session, actor=actor)
    await service.transition_segment(
        db_session, actor=actor, segment=segment, target_status="active"
    )
    with pytest.raises(SegmentError):
        await service.transition_segment(
            db_session, actor=actor, segment=segment, target_status="draft"
        )


# --- Static membership: immutable history, latest-action-wins --------------


async def test_static_member_add_then_remove_then_add_again_reflects_latest_state(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    segment = await _make_segment(db_session, actor=actor, segment_type="static")
    customer = await _make_customer(db_session)

    await membership.add_static_member(
        db_session, segment=segment, customer_id=customer.id, actor=actor, reason="join"
    )
    members = await membership.get_current_member_ids(db_session, segment.id)
    assert customer.id in members

    await membership.remove_static_member(
        db_session, segment=segment, customer_id=customer.id, actor=actor, reason="leave"
    )
    members = await membership.get_current_member_ids(db_session, segment.id)
    assert customer.id not in members

    await membership.add_static_member(
        db_session, segment=segment, customer_id=customer.id, actor=actor, reason="rejoin"
    )
    members = await membership.get_current_member_ids(db_session, segment.id)
    assert customer.id in members

    # Every add/remove call produced its own immutable row — never an
    # in-place edit of a prior row.
    ids, total = await membership.list_members(
        db_session, segment_id=segment.id, page=1, page_size=25
    )
    assert total == 1
    assert ids == [customer.id]


async def test_static_membership_on_wrong_segment_type_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    segment = await _make_segment(db_session, actor=actor, segment_type="dynamic")
    customer = await _make_customer(db_session)
    with pytest.raises(WrongSegmentTypeError):
        await membership.add_static_member(
            db_session, segment=segment, customer_id=customer.id, actor=actor, reason=None
        )


# --- Dynamic segment refresh against real customer data ----------------------


async def test_refresh_materializes_only_matching_customers(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    high_value = await _make_customer(db_session, lifetime_value_minor=100_000)
    low_value = await _make_customer(db_session, lifetime_value_minor=100)

    rule = RuleCondition(fact="customer.lifetime_spend_minor", operator="gte", value=50_000)
    segment = await service.create_segment(
        db_session,
        actor=actor,
        payload=SegmentCreateIn(
            code=_segment_code(), name="High value", segment_type="dynamic", rule_definition=rule
        ),
    )

    computed_count = await membership.refresh(db_session, segment=segment)

    members = await membership.get_current_member_ids(db_session, segment.id)
    assert high_value.id in members
    assert low_value.id not in members
    assert computed_count == len(members)
    assert segment.last_computed_count == computed_count
    assert segment.estimated_count == computed_count
    assert segment.last_refreshed_at is not None


async def test_refresh_removes_customers_who_no_longer_match(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session, lifetime_value_minor=100_000)

    rule = RuleCondition(fact="customer.lifetime_spend_minor", operator="gte", value=50_000)
    segment = await service.create_segment(
        db_session,
        actor=actor,
        payload=SegmentCreateIn(
            code=_segment_code(), name="High value", segment_type="dynamic", rule_definition=rule
        ),
    )
    await membership.refresh(db_session, segment=segment)
    members = await membership.get_current_member_ids(db_session, segment.id)
    assert customer.id in members

    customer.lifetime_value_minor = 0
    await db_session.flush()
    await membership.refresh(db_session, segment=segment)
    members = await membership.get_current_member_ids(db_session, segment.id)
    assert customer.id not in members


async def test_refresh_twice_with_no_data_change_does_not_duplicate_history(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    await _make_customer(db_session, lifetime_value_minor=100_000)

    rule = RuleCondition(fact="customer.lifetime_spend_minor", operator="gte", value=50_000)
    segment = await service.create_segment(
        db_session,
        actor=actor,
        payload=SegmentCreateIn(
            code=_segment_code(), name="High value", segment_type="dynamic", rule_definition=rule
        ),
    )
    await membership.refresh(db_session, segment=segment)
    _, total_after_first = await membership.list_members(
        db_session, segment_id=segment.id, page=1, page_size=25
    )

    await membership.refresh(db_session, segment=segment)
    _, total_after_second = await membership.list_members(
        db_session, segment_id=segment.id, page=1, page_size=25
    )
    assert total_after_first == total_after_second == 1

    from app.db.models import SegmentMembership
    from sqlalchemy import func, select

    row_count = await db_session.scalar(
        select(func.count())
        .select_from(SegmentMembership)
        .where(SegmentMembership.segment_id == segment.id)
    )
    assert row_count == 1  # only the original "added" row — refresh #2 wrote nothing


async def test_refresh_on_static_segment_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    segment = await _make_segment(db_session, actor=actor, segment_type="static")
    with pytest.raises(WrongSegmentTypeError):
        await membership.refresh(db_session, segment=segment)


async def test_evaluate_for_customer_reflects_rule_outcome(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session, lifetime_value_minor=100_000)
    rule = RuleCondition(fact="customer.lifetime_spend_minor", operator="gte", value=50_000)
    segment = await service.create_segment(
        db_session,
        actor=actor,
        payload=SegmentCreateIn(
            code=_segment_code(), name="High value", segment_type="dynamic", rule_definition=rule
        ),
    )
    result = await membership.evaluate_for_customer(
        db_session, segment=segment, customer_id=customer.id
    )
    assert result.eligible is True
    assert result.matched_facts == ["customer.lifetime_spend_minor"]
