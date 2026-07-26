"""Idempotent development seed data for leads — PROJECT_PLAN.md section 6,
CORE_CRM_MODULES.md section 5. Covers all five sources this phase names
directly (Zomato, Swiggy, Website, Marketing Campaign, Offline), a range
of statuses, an overdue follow-up, an unassigned lead, a lost lead, and a
do-not-contact lead — enough to exercise every filter and state this
phase's frontend needs to demonstrate. Conversion itself is exercised by
`test_lead_conversion.py`, not pre-seeded here, since a realistic
converted-lead fixture requires actually running the conversion service
(idempotency key, resulting customer) rather than hand-writing its result.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lead, LeadFollowUp, LeadStatusHistory, StaffUser
from app.leads.service import generate_lead_number


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    stmt = select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    result = await session.scalar(stmt)
    return result


async def _get_or_create_lead(
    session: AsyncSession,
    *,
    display_name: str,
    source: str,
    actor: StaffUser | None,
    **fields: object,
) -> tuple[Lead, bool]:
    existing = await session.scalar(
        select(Lead).where(Lead.display_name == display_name, Lead.source == source)
    )
    if existing is not None:
        return existing, False

    lead_status = fields.pop("status", "new")
    lead = Lead(
        id=uuid.uuid4(),
        lead_number=generate_lead_number(),
        display_name=display_name,
        source=source,
        status=lead_status,
        created_by=actor.id if actor else None,
        **fields,
    )
    session.add(lead)
    await session.flush()
    session.add(
        LeadStatusHistory(
            id=uuid.uuid4(),
            lead_id=lead.id,
            previous_status=None,
            new_status=lead.status,
            actor_id=actor.id if actor else None,
        )
    )
    return lead, True


async def seed_leads(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    now = datetime.now(UTC)

    await _get_or_create_lead(
        session,
        display_name="BrightWave Technologies",
        source="website",
        actor=actor,
        lead_type="corporate_catering",
        organization_name="BrightWave Technologies",
        contact_name="Nikhil Jain",
        phone_e164="+919876500010",
        status="qualified",
        priority="high",
        estimated_value_minor=1_800_000,
        party_size=60,
        description="Corporate lunch for 60 staff.",
    )

    await _get_or_create_lead(
        session,
        display_name="Priya Birthday Event",
        source="whatsapp",
        actor=actor,
        lead_type="event_booking",
        phone_e164="+919876500011",
        status="follow_up_scheduled",
        priority="normal",
        estimated_value_minor=2_200_000,
        party_size=25,
        description="25-guest birthday event.",
    )

    await _get_or_create_lead(
        session,
        display_name="EastPoint College Fest",
        source="referral",
        actor=actor,
        lead_type="group_dining",
        status="negotiating",
        priority="normal",
        estimated_value_minor=4_800_000,
        party_size=120,
        description="120 meal boxes for a college fest.",
    )

    await _get_or_create_lead(
        session,
        display_name="Zomato Walk-in Enquiry",
        source="zomato_import",
        actor=actor,
        lead_type="general_sales_enquiry",
        status="new",
        priority="low",
    )

    await _get_or_create_lead(
        session,
        display_name="Swiggy Catering Enquiry",
        source="swiggy_import",
        actor=actor,
        lead_type="corporate_catering",
        status="contacted",
        priority="normal",
    )

    await _get_or_create_lead(
        session,
        display_name="Instagram Campaign Enquiry",
        source="meta_campaign",
        actor=actor,
        lead_type="general_sales_enquiry",
        status="interested",
        priority="low",
        campaign_reference="Diwali 2026 Instagram promo",
    )

    overdue_lead, created = await _get_or_create_lead(
        session,
        display_name="Overdue Franchise Enquiry",
        source="offline_qr",
        actor=actor,
        lead_type="franchise_or_business_enquiry",
        status="follow_up_scheduled",
        priority="urgent",
        assigned_staff_id=actor.id if actor else None,
        next_follow_up_at=now - timedelta(days=2),
    )
    if created:
        session.add(
            LeadFollowUp(
                id=uuid.uuid4(),
                lead_id=overdue_lead.id,
                assigned_to=actor.id if actor else uuid.uuid4(),
                scheduled_at=now - timedelta(days=2),
                status="scheduled",
                purpose="Call back about franchise terms.",
                created_by=actor.id if actor else None,
            )
        )

    await _get_or_create_lead(
        session,
        display_name="Lost Corporate Enquiry",
        source="corporate_outreach",
        actor=actor,
        lead_type="corporate_catering",
        status="lost",
        lost_reason="budget",
        priority="normal",
    )

    await _get_or_create_lead(
        session,
        display_name="Do Not Contact Enquiry",
        source="phone",
        actor=actor,
        lead_type="general_sales_enquiry",
        status="contacted",
        do_not_contact=True,
    )
