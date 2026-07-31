"""Audience resolution and snapshot materialization —
GROWTH_AND_INTELLIGENCE.md section 3.10: "Eligibility must be calculated
at send time, not frozen only at campaign creation." Building the
audience only resolves *who* is targeted (segment membership, minus
exclusions) into one `CampaignRecipient` row per (customer, channel);
consent/suppression/frequency eligibility is evaluated separately, at
launch time, in `app.campaigns.execution`.

Matches `Segment`'s own docstring: a campaign audience is a snapshot
taken once (`Campaign.audience_snapshot_taken_at`), never a live
re-evaluation, so later segment edits cannot alter a campaign's history.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.campaigns.errors import CampaignError
from app.db.models import Campaign, CampaignRecipient, Segment
from app.segments.membership import get_current_member_ids
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _resolve_audience(
    session: AsyncSession, campaign: Campaign
) -> dict[uuid.UUID, uuid.UUID]:
    """Returns {customer_id: source_segment_id} for the resolved audience —
    the segment a customer is attributed to is the first target segment
    (in configured order) whose membership includes them."""
    included: dict[uuid.UUID, uuid.UUID] = {}
    for raw_id in campaign.target_segment_ids:
        segment = await session.get(Segment, uuid.UUID(raw_id))
        if segment is None:
            continue
        for customer_id in await get_current_member_ids(session, segment.id):
            included.setdefault(customer_id, segment.id)

    excluded: set[uuid.UUID] = set()
    for raw_id in campaign.excluded_segment_ids or []:
        segment = await session.get(Segment, uuid.UUID(raw_id))
        if segment is None:
            continue
        excluded |= await get_current_member_ids(session, segment.id)

    for customer_id in excluded:
        included.pop(customer_id, None)
    return included


async def build_audience(session: AsyncSession, *, campaign: Campaign) -> int:
    if campaign.status not in ("draft", "ready"):
        raise CampaignError(
            f"Campaign {campaign.code!r} is {campaign.status!r}; audience can only be "
            "(re)built while draft or ready."
        )

    audience = await _resolve_audience(session, campaign)
    channel_ids = [uuid.UUID(c) for c in campaign.channel_templates]

    existing_pairs = set(
        await session.execute(
            select(CampaignRecipient.customer_id, CampaignRecipient.channel_id).where(
                CampaignRecipient.campaign_id == campaign.id
            )
        )
    )

    now = datetime.now(UTC)
    created = 0
    for customer_id, source_segment_id in audience.items():
        for channel_id in channel_ids:
            if (customer_id, channel_id) in existing_pairs:
                continue
            session.add(
                CampaignRecipient(
                    id=uuid.uuid4(),
                    campaign_id=campaign.id,
                    customer_id=customer_id,
                    channel_id=channel_id,
                    source_segment_id=source_segment_id,
                    status="pending",
                    attempt_count=0,
                    created_at=now,
                )
            )
            created += 1

    total = len(existing_pairs) + created
    campaign.estimated_size = total
    campaign.audience_snapshot_taken_at = now
    await session.flush()
    return total
