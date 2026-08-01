"""Idempotent development seed data for complaints and SLA policies.
Reuses `app.complaints.service`/`app.complaints.sla` directly rather than
constructing rows by hand — the same precedent every prior phase's own
`seed_*()` sets. Run after `app.feedback.seed.seed_feedback` (the
Karthik complaint below is produced by that seed's own feedback-to-
complaint conversion, not duplicated here)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.complaints import service, sla
from app.complaints.schemas import ComplaintCreateIn, SlaPolicyCreateIn
from app.db.models import Complaint, Customer, SlaPolicy, StaffUser


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    result: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    return result


async def _customer_id(session: AsyncSession, email: str) -> uuid.UUID | None:
    result: uuid.UUID | None = await session.scalar(
        select(Customer.id).where(Customer.primary_email == email)
    )
    return result


async def _seed_sla_policy(session: AsyncSession) -> None:
    existing = await session.scalar(select(SlaPolicy).where(SlaPolicy.code == "standard_sla"))
    if existing is not None:
        return
    await sla.create_sla_policy(
        session,
        payload=SlaPolicyCreateIn(
            code="standard_sla",
            name="Standard Complaint SLA",
            first_response_minutes=60,
            acknowledgement_minutes=120,
            resolution_minutes=1440,
            follow_up_minutes=4320,
            escalation_after_minutes=2880,
            business_hours_only=False,
        ),
    )


async def seed_complaints(session: AsyncSession) -> None:
    await _seed_sla_policy(session)

    actor = await _system_actor(session)
    if actor is None:
        return

    shreya_id = await _customer_id(session, "shreya.kulkarni@example.test")
    if shreya_id is not None:
        existing = await session.scalar(
            select(Complaint).where(
                Complaint.customer_id == shreya_id, Complaint.category == "delay"
            )
        )
        if existing is None:
            complaint = await service.create_complaint(
                session,
                actor=actor,
                payload=ComplaintCreateIn(
                    customer_id=shreya_id,
                    source_type="direct",
                    category="delay",
                    title="Order delivered over an hour past the promised window",
                    description=(
                        "Customer called in — order confirmed at 7:10pm, promised for 7:45pm, "
                        "actually arrived at 9:05pm with no proactive update."
                    ),
                    severity="high",
                    priority="high",
                    channel="phone",
                ),
            )
            await service.assign_complaint(
                session,
                actor=actor,
                complaint=complaint,
                assigned_staff_id=actor.id,
                assigned_department_id=None,
                reason="Initial triage.",
            )
            await service.add_note(
                session,
                actor=actor,
                complaint=complaint,
                note="Called customer to apologize; offering compensation for review.",
            )
            follow_up = await service.schedule_follow_up(
                session,
                actor=actor,
                complaint=complaint,
                scheduled_at=datetime.now(UTC) + timedelta(days=2),
                notes="Confirm customer satisfaction after compensation is issued.",
            )
            await service.complete_follow_up(
                session,
                actor=actor,
                follow_up=follow_up,
                outcome="satisfied",
                notes="Customer confirmed satisfaction after the complimentary item credit.",
            )

    priya_id = await _customer_id(session, "priya.sharma@example.test")
    if priya_id is not None:
        existing = await session.scalar(
            select(Complaint).where(
                Complaint.customer_id == priya_id, Complaint.category == "staff_behavior"
            )
        )
        if existing is None:
            complaint = await service.create_complaint(
                session,
                actor=actor,
                payload=ComplaintCreateIn(
                    customer_id=priya_id,
                    source_type="direct",
                    category="staff_behavior",
                    title="Customer reports dismissive treatment by front-of-house staff",
                    description=(
                        "Customer says a staff member was dismissive when asking about an "
                        "allergy substitution during dine-in service."
                    ),
                    severity="critical",
                    priority="urgent",
                    channel="in_person",
                ),
            )
            await service.assign_complaint(
                session,
                actor=actor,
                complaint=complaint,
                assigned_staff_id=actor.id,
                assigned_department_id=None,
                reason="HR-sensitive — routed to management directly.",
            )
            await service.transition_complaint(
                session,
                actor=actor,
                complaint=complaint,
                target_status="acknowledged",
                reason="Acknowledged with customer; investigation opened with HR.",
            )
            await service.transition_complaint(
                session,
                actor=actor,
                complaint=complaint,
                target_status="investigating",
                reason="Gathering statements from on-shift staff.",
            )
