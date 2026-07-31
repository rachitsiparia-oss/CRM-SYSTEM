"""Idempotent development seed data for Campaigns — one draft welcome-back
campaign targeting the seeded "New Customers" segment over email, reusing
Phase 10's Communication Hub end to end (a real `MessageTemplate`, not a
new channel). Left in `draft` — this phase's own instruction against
seeding a campaign that appears already launched.
"""

from __future__ import annotations

from app.campaigns import service
from app.campaigns.schemas import CampaignCreateIn
from app.communications.schemas import MessageTemplateCreateIn
from app.communications.templates import create_template
from app.db.models import CommunicationChannel, MessageTemplate, StaffUser
from app.segments import service as segments_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def seed_campaigns(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    segment = await segments_service.get_segment_by_code(session, "new_customers")
    if segment is None:
        return

    existing = await service.get_campaign_by_code(session, "welcome_series_email")
    if existing is not None:
        return

    channel = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.code == "email")
    )
    if channel is None:
        return

    template = await session.scalar(
        select(MessageTemplate).where(MessageTemplate.code == "welcome_series")
    )
    if template is None:
        template = await create_template(
            session,
            actor=actor,
            payload=MessageTemplateCreateIn(
                name="Welcome Series",
                code="welcome_series",
                channel_id=channel.id,
                category="general",
                subject="Welcome to RKPR!",
                body="Hi {customer_name}, welcome to RKPR — enjoy 10% off your first order "
                "with WELCOME10.",
                variables=["customer_name"],
                is_transactional=False,
            ),
        )
        template.status = "active"
        await session.flush()

    await service.create_campaign(
        session,
        actor=actor,
        payload=CampaignCreateIn(
            code="welcome_series_email",
            name="Welcome Series — Email",
            objective="onboarding",
            campaign_type="lifecycle",
            channel_templates={str(channel.id): str(template.id)},
            target_segment_ids=[segment.id],
        ),
    )
