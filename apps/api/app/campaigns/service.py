"""Campaign configuration CRUD and status lifecycle —
GROWTH_AND_INTELLIGENCE.md section 3.3/3.9. Per section 3.9's "later edits
must return the campaign to a review-required state unless... explicitly
non-substantive": any edit to a `ready` campaign resets it to `draft` so
it must be re-approved; edits are blocked entirely once a campaign has
left draft/ready (scheduled/running/etc.) since a change to a launched
campaign cannot rewrite what was already sent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.audit.service import record_audit_event
from app.campaigns.errors import DuplicateCampaignCodeError, InvalidStatusTransitionError
from app.campaigns.schemas import CampaignCreateIn, CampaignStatus, CampaignUpdateIn
from app.db.models import Campaign, StaffUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_CAMPAIGN_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"ready", "cancelled"},
    "ready": {"scheduled", "draft", "cancelled"},
    "scheduled": {"running", "cancelled"},
    "running": {"paused", "completed", "cancelled", "failed"},
    "paused": {"running", "cancelled"},
    "completed": {"archived"},
    "cancelled": {"archived"},
    "failed": {"archived"},
    "archived": set(),
}

_EDITABLE_STATUSES = {"draft", "ready"}


async def list_campaigns(
    session: AsyncSession, *, page: int, page_size: int, status: str | None = None
) -> tuple[list[Campaign], int]:
    query = select(Campaign)
    count_query = select(func.count()).select_from(Campaign)
    if status is not None:
        query = query.where(Campaign.status == status)
        count_query = count_query.where(Campaign.status == status)

    total = await session.scalar(count_query)
    rows = await session.scalars(
        query.order_by(Campaign.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rows), total or 0


async def get_campaign(session: AsyncSession, campaign_id: uuid.UUID) -> Campaign | None:
    return await session.get(Campaign, campaign_id)


async def get_campaign_by_code(session: AsyncSession, code: str) -> Campaign | None:
    result: Campaign | None = await session.scalar(select(Campaign).where(Campaign.code == code))
    return result


async def create_campaign(
    session: AsyncSession, *, actor: StaffUser, payload: CampaignCreateIn
) -> Campaign:
    existing = await get_campaign_by_code(session, payload.code)
    if existing is not None:
        raise DuplicateCampaignCodeError(f"Campaign code {payload.code!r} is already in use.")

    campaign = Campaign(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        objective=payload.objective,
        campaign_type=payload.campaign_type,
        status="draft",
        channel_templates=payload.channel_templates,
        target_segment_ids=[str(s) for s in payload.target_segment_ids],
        excluded_segment_ids=(
            [str(s) for s in payload.excluded_segment_ids] if payload.excluded_segment_ids else None
        ),
        linked_offer_id=payload.linked_offer_id,
        scheduled_at=payload.scheduled_at,
        send_window_start_local=payload.send_window_start_local,
        send_window_end_local=payload.send_window_end_local,
        budget_minor=payload.budget_minor,
        owner_staff_id=payload.owner_staff_id or actor.id,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(campaign)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="campaign.created",
        target_type="campaign",
        target_id=campaign.id,
        safe_metadata={"code": campaign.code},
    )
    return campaign


async def update_campaign(
    session: AsyncSession, *, actor: StaffUser, campaign: Campaign, payload: CampaignUpdateIn
) -> Campaign:
    if campaign.status not in _EDITABLE_STATUSES:
        raise InvalidStatusTransitionError(
            f"Campaign {campaign.code!r} is {campaign.status!r} and can no longer be edited."
        )

    if payload.name is not None:
        campaign.name = payload.name
    if payload.objective is not None:
        campaign.objective = payload.objective
    if payload.campaign_type is not None:
        campaign.campaign_type = payload.campaign_type
    if payload.channel_templates is not None:
        campaign.channel_templates = payload.channel_templates
    if payload.target_segment_ids is not None:
        campaign.target_segment_ids = [str(s) for s in payload.target_segment_ids]
    if payload.excluded_segment_ids is not None:
        campaign.excluded_segment_ids = [str(s) for s in payload.excluded_segment_ids]
    if payload.linked_offer_id is not None:
        campaign.linked_offer_id = payload.linked_offer_id
    if payload.scheduled_at is not None:
        campaign.scheduled_at = payload.scheduled_at
    if payload.send_window_start_local is not None:
        campaign.send_window_start_local = payload.send_window_start_local
    if payload.send_window_end_local is not None:
        campaign.send_window_end_local = payload.send_window_end_local
    if payload.budget_minor is not None:
        campaign.budget_minor = payload.budget_minor
    if payload.owner_staff_id is not None:
        campaign.owner_staff_id = payload.owner_staff_id

    if campaign.status == "ready":
        campaign.status = "draft"
    campaign.updated_by = actor.id
    await session.flush()
    return campaign


async def transition_campaign(
    session: AsyncSession,
    *,
    actor: StaffUser,
    campaign: Campaign,
    target_status: CampaignStatus,
    reason: str | None,
) -> Campaign:
    allowed = _CAMPAIGN_TRANSITIONS.get(campaign.status, set())
    if target_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition campaign from {campaign.status!r} to {target_status!r}."
        )

    now = datetime.now(UTC)
    if target_status == "scheduled":
        campaign.approved_by = actor.id
        campaign.approved_at = now
    if target_status == "running" and campaign.started_at is None:
        campaign.started_at = now
    if target_status == "completed":
        campaign.completed_at = now
    if target_status in ("cancelled", "failed") and reason:
        campaign.cancelled_reason = reason

    campaign.status = target_status
    campaign.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="campaign.transitioned",
        target_type="campaign",
        target_id=campaign.id,
        safe_metadata={"target_status": target_status, "reason": reason},
    )
    return campaign
