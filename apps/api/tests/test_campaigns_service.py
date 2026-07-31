"""Campaign audience materialization and status-lifecycle tests —
`app.campaigns.audience` and `app.campaigns.service`.

Covers: `build_audience` produces one `CampaignRecipient` row per
(customer, channel) pair from the segment's resolved membership and is
safe to call twice without duplicating rows; a campaign cannot be edited
once it has left draft/ready; and per this module's own docstring
("any edit to a `ready` campaign resets it to `draft` so it must be
re-approved") editing a `ready` campaign resets it back to `draft` — this
is verified against the actual `update_campaign` implementation
(`app/campaigns/service.py` lines 136-137), not merely assumed from the
docstring.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.campaigns import audience, service
from app.campaigns.errors import InvalidStatusTransitionError
from app.campaigns.schemas import CampaignCreateIn, CampaignStatus, CampaignUpdateIn
from app.db.models import Campaign, CampaignRecipient, CommunicationChannel, Customer, StaffUser
from app.segments import service as segments_service
from app.segments.membership import add_static_member
from app.segments.schemas import SegmentCreateIn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def _make_customer(session: AsyncSession) -> Customer:
    suffix = uuid.uuid4().hex[:10]
    customer = Customer(
        id=uuid.uuid4(),
        customer_number=f"CUST-{suffix}",
        display_name="Test Customer",
        first_name="Test",
        last_name="Customer",
    )
    session.add(customer)
    await session.flush()
    return customer


async def _get_or_create_channel(
    session: AsyncSession, *, code: str = "email"
) -> CommunicationChannel:
    existing = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.code == code)
    )
    if existing is not None:
        return existing
    channel = CommunicationChannel(id=uuid.uuid4(), code=code, name=code.title())
    session.add(channel)
    await session.flush()
    return channel


async def _make_static_segment_with_members(
    session: AsyncSession, *, actor: StaffUser, customers: list[Customer]
) -> uuid.UUID:
    suffix = uuid.uuid4().hex[:10]
    segment = await segments_service.create_segment(
        session,
        actor=actor,
        payload=SegmentCreateIn(code=f"seg-{suffix}", name="Test Segment", segment_type="static"),
    )
    for customer in customers:
        await add_static_member(
            session, segment=segment, customer_id=customer.id, actor=actor, reason=None
        )
    return segment.id


async def _make_campaign(
    session: AsyncSession,
    *,
    actor: StaffUser,
    segment_id: uuid.UUID,
    channel_id: uuid.UUID,
    **overrides: Any,
) -> Campaign:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, Any] = {
        "code": f"camp-{suffix}",
        "name": "Test Campaign",
        "channel_templates": {str(channel_id): str(uuid.uuid4())},
        "target_segment_ids": [segment_id],
    }
    fields.update(overrides)
    return await service.create_campaign(session, actor=actor, payload=CampaignCreateIn(**fields))


# --- build_audience ---------------------------------------------------------


async def test_build_audience_materializes_one_recipient_per_customer_channel_pair(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    channel = await _get_or_create_channel(db_session)
    customer_a = await _make_customer(db_session)
    customer_b = await _make_customer(db_session)
    segment_id = await _make_static_segment_with_members(
        db_session, actor=actor, customers=[customer_a, customer_b]
    )
    campaign = await _make_campaign(
        db_session, actor=actor, segment_id=segment_id, channel_id=channel.id
    )

    total = await audience.build_audience(db_session, campaign=campaign)
    assert total == 2

    rows = list(
        await db_session.scalars(
            select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id)
        )
    )
    assert len(rows) == 2
    assert {row.customer_id for row in rows} == {customer_a.id, customer_b.id}
    assert all(row.channel_id == channel.id for row in rows)
    assert all(row.status == "pending" for row in rows)


async def test_build_audience_is_safe_to_call_twice_without_duplicating_rows(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    channel = await _get_or_create_channel(db_session)
    customer = await _make_customer(db_session)
    segment_id = await _make_static_segment_with_members(
        db_session, actor=actor, customers=[customer]
    )
    campaign = await _make_campaign(
        db_session, actor=actor, segment_id=segment_id, channel_id=channel.id
    )

    first_total = await audience.build_audience(db_session, campaign=campaign)
    second_total = await audience.build_audience(db_session, campaign=campaign)
    assert first_total == 1
    assert second_total == 1

    rows = list(
        await db_session.scalars(
            select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id)
        )
    )
    assert len(rows) == 1


# --- update_campaign editability and the ready->draft reset rule -----------


async def test_update_campaign_blocked_once_scheduled(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    channel = await _get_or_create_channel(db_session)
    customer = await _make_customer(db_session)
    segment_id = await _make_static_segment_with_members(
        db_session, actor=actor, customers=[customer]
    )
    campaign = await _make_campaign(
        db_session, actor=actor, segment_id=segment_id, channel_id=channel.id
    )
    await service.transition_campaign(
        db_session, actor=actor, campaign=campaign, target_status="ready", reason=None
    )
    await service.transition_campaign(
        db_session, actor=actor, campaign=campaign, target_status="scheduled", reason=None
    )

    with pytest.raises(InvalidStatusTransitionError):
        await service.update_campaign(
            db_session,
            actor=actor,
            campaign=campaign,
            payload=CampaignUpdateIn(name="New name"),
        )


async def test_editing_a_ready_campaign_resets_it_to_draft(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    """Verifies the module docstring's documented "review-required after
    edit" behavior against the real implementation, per this task's own
    instruction to test actual behavior rather than assume it."""
    actor = await make_staff_user(role_code="owner")
    channel = await _get_or_create_channel(db_session)
    customer = await _make_customer(db_session)
    segment_id = await _make_static_segment_with_members(
        db_session, actor=actor, customers=[customer]
    )
    campaign = await _make_campaign(
        db_session, actor=actor, segment_id=segment_id, channel_id=channel.id
    )
    await service.transition_campaign(
        db_session, actor=actor, campaign=campaign, target_status="ready", reason=None
    )
    assert campaign.status == "ready"

    updated = await service.update_campaign(
        db_session,
        actor=actor,
        campaign=campaign,
        payload=CampaignUpdateIn(name="Edited after ready"),
    )
    assert updated.name == "Edited after ready"
    assert updated.status == "draft"


async def test_editing_a_draft_campaign_leaves_it_in_draft(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    channel = await _get_or_create_channel(db_session)
    customer = await _make_customer(db_session)
    segment_id = await _make_static_segment_with_members(
        db_session, actor=actor, customers=[customer]
    )
    campaign = await _make_campaign(
        db_session, actor=actor, segment_id=segment_id, channel_id=channel.id
    )
    assert campaign.status == "draft"

    updated = await service.update_campaign(
        db_session, actor=actor, campaign=campaign, payload=CampaignUpdateIn(name="Still draft")
    )
    assert updated.status == "draft"


# --- transition state machine ------------------------------------------


async def test_transition_campaign_rejects_invalid_transition(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    channel = await _get_or_create_channel(db_session)
    customer = await _make_customer(db_session)
    segment_id = await _make_static_segment_with_members(
        db_session, actor=actor, customers=[customer]
    )
    campaign = await _make_campaign(
        db_session, actor=actor, segment_id=segment_id, channel_id=channel.id
    )

    with pytest.raises(InvalidStatusTransitionError):
        await service.transition_campaign(
            db_session, actor=actor, campaign=campaign, target_status="running", reason=None
        )


async def test_transition_campaign_happy_path_sets_timestamps(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    channel = await _get_or_create_channel(db_session)
    customer = await _make_customer(db_session)
    segment_id = await _make_static_segment_with_members(
        db_session, actor=actor, customers=[customer]
    )
    campaign = await _make_campaign(
        db_session, actor=actor, segment_id=segment_id, channel_id=channel.id
    )

    targets: tuple[CampaignStatus, ...] = ("ready", "scheduled", "running", "completed", "archived")
    for target in targets:
        campaign = await service.transition_campaign(
            db_session, actor=actor, campaign=campaign, target_status=target, reason=None
        )
        assert campaign.status == target

    assert campaign.approved_by == actor.id
    assert campaign.approved_at is not None
    assert campaign.started_at is not None
    assert campaign.completed_at is not None
