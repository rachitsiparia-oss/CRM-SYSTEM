"""Lead business logic — CORE_CRM_MODULES.md section 5, DATABASE_AND_API.md
section 7. Kept out of the router for the same reason as
app.customers.service and app.staff.service (Phase 3 precedent):
state-machine and conversion behavior needs to be unit-testable without an
HTTP client.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.customers.service import derive_display_name, generate_customer_number
from app.db.models import Customer, Lead, LeadActivity, LeadFollowUp, LeadStatusHistory, StaffUser
from app.db.models.lead_activity import CONTACT_ACTIVITY_TYPES
from app.leads.schemas import LeadCreateIn, LeadUpdateIn
from app.leads.states import is_transition_allowed
from app.outbox.service import record_domain_event


def generate_lead_number() -> str:
    return f"LEAD-{uuid.uuid4().hex[:8].upper()}"


async def find_duplicate_leads(
    session: AsyncSession,
    *,
    phone: str | None,
    email: str | None,
    exclude_id: uuid.UUID | None = None,
) -> list[tuple[Lead, list[str]]]:
    if not phone and not email:
        return []

    conditions = []
    if phone:
        conditions.append(Lead.phone_e164 == phone)
    if email:
        conditions.append(Lead.email == email)

    stmt = select(Lead).where(or_(*conditions), Lead.deleted_at.is_(None))
    if exclude_id is not None:
        stmt = stmt.where(Lead.id != exclude_id)

    candidates = (await session.scalars(stmt)).all()
    results: list[tuple[Lead, list[str]]] = []
    for candidate in candidates:
        reasons = []
        if phone and candidate.phone_e164 == phone:
            reasons.append("exact_normalized_phone")
        if email and candidate.email == email:
            reasons.append("exact_normalized_email")
        results.append((candidate, reasons))
    return results


async def create_lead(
    session: AsyncSession, *, actor: StaffUser, payload: LeadCreateIn, request: Request | None
) -> Lead:
    lead = Lead(
        id=uuid.uuid4(),
        lead_number=generate_lead_number(),
        lead_type=payload.lead_type,
        display_name=payload.display_name,
        organization_name=payload.organization_name,
        contact_name=payload.contact_name,
        phone_e164=payload.phone_e164,
        email=payload.email,
        source=payload.source,
        campaign_reference=payload.campaign_reference,
        status="new",
        priority=payload.priority,
        estimated_value_minor=payload.estimated_value_minor,
        party_size=payload.party_size,
        requested_date=payload.requested_date,
        requested_time=payload.requested_time,
        assigned_staff_id=payload.assigned_staff_id,
        description=payload.description,
        qualification_notes=payload.qualification_notes,
        food_preferences=payload.food_preferences,
        budget_notes=payload.budget_notes,
        created_by=actor.id,
    )
    session.add(lead)
    await session.flush()

    session.add(
        LeadStatusHistory(
            id=uuid.uuid4(),
            lead_id=lead.id,
            previous_status=None,
            new_status="new",
            actor_id=actor.id,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.created",
        target_type="lead",
        target_id=lead.id,
        request=request,
        safe_metadata={"lead_number": lead.lead_number, "source": lead.source},
    )
    await record_domain_event(
        session,
        event_type="lead.created",
        aggregate_type="lead",
        aggregate_id=lead.id,
        payload={"lead_id": str(lead.id), "lead_number": lead.lead_number, "source": lead.source},
    )
    return lead


async def update_lead(
    session: AsyncSession,
    *,
    actor: StaffUser,
    lead: Lead,
    payload: LeadUpdateIn,
    request: Request | None,
) -> Lead:
    if payload.expected_version is not None and payload.expected_version != lead.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This lead was updated by someone else. Reload and try again.",
        )

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = {field: getattr(lead, field) for field in updates}
    for field, value in updates.items():
        setattr(lead, field, value)

    if updates:
        lead.version += 1
        lead.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="lead.updated",
            target_type="lead",
            target_id=lead.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return lead


async def assign_lead(
    session: AsyncSession,
    *,
    actor: StaffUser,
    lead: Lead,
    assigned_staff_id: uuid.UUID,
    request: Request | None,
) -> None:
    before = lead.assigned_staff_id
    lead.assigned_staff_id = assigned_staff_id
    lead.updated_by = actor.id
    lead.version += 1

    session.add(
        LeadActivity(
            id=uuid.uuid4(),
            lead_id=lead.id,
            activity_type="assignment",
            summary=f"Assigned to staff member {assigned_staff_id}.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.assigned",
        target_type="lead",
        target_id=lead.id,
        request=request,
        before_summary={"assigned_staff_id": str(before) if before else None},
        after_summary={"assigned_staff_id": str(assigned_staff_id)},
    )


async def transition_lead(
    session: AsyncSession,
    *,
    actor: StaffUser,
    lead: Lead,
    new_status: str,
    reason: str | None,
    lost_reason: str | None,
    request: Request | None,
) -> None:
    if not is_transition_allowed(lead.status, new_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move a lead from '{lead.status}' to '{new_status}'.",
        )
    if new_status == "lost" and not lost_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lost_reason is required when marking a lead lost.",
        )

    previous_status = lead.status
    lead.status = new_status
    lead.updated_by = actor.id
    lead.version += 1
    if new_status == "lost":
        lead.lost_reason = lost_reason
    elif previous_status == "lost":
        lead.lost_reason = None

    session.add(
        LeadStatusHistory(
            id=uuid.uuid4(),
            lead_id=lead.id,
            previous_status=previous_status,
            new_status=new_status,
            actor_id=actor.id,
            reason=reason or lost_reason,
        )
    )
    session.add(
        LeadActivity(
            id=uuid.uuid4(),
            lead_id=lead.id,
            activity_type="status_change",
            summary=f"Status changed from {previous_status} to {new_status}.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.status_changed",
        target_type="lead",
        target_id=lead.id,
        request=request,
        before_summary={"status": previous_status},
        after_summary={"status": new_status},
        safe_metadata={"reason": reason, "lost_reason": lost_reason},
    )
    await record_domain_event(
        session,
        event_type="lead.stage_changed",
        aggregate_type="lead",
        aggregate_id=lead.id,
        payload={
            "lead_id": str(lead.id),
            "previous_status": previous_status,
            "new_status": new_status,
        },
    )


async def set_do_not_contact(
    session: AsyncSession, *, actor: StaffUser, lead: Lead, value: bool, request: Request | None
) -> None:
    lead.do_not_contact = value
    lead.updated_by = actor.id
    lead.version += 1
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.do_not_contact_changed",
        target_type="lead",
        target_id=lead.id,
        request=request,
        safe_metadata={"do_not_contact": value},
    )


async def archive_lead(
    session: AsyncSession, *, actor: StaffUser, lead: Lead, reason: str, request: Request | None
) -> None:
    lead.deleted_at = datetime.now(UTC)
    lead.deleted_by = actor.id
    lead.deletion_reason = reason
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.archived",
        target_type="lead",
        target_id=lead.id,
        request=request,
        safe_metadata={"reason": reason},
    )


async def restore_lead(
    session: AsyncSession, *, actor: StaffUser, lead: Lead, request: Request | None
) -> None:
    lead.deleted_at = None
    lead.deleted_by = None
    lead.deletion_reason = None
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.restored",
        target_type="lead",
        target_id=lead.id,
        request=request,
    )


async def add_activity(
    session: AsyncSession,
    *,
    actor: StaffUser,
    lead: Lead,
    activity_type: str,
    summary: str,
    occurred_at: datetime | None,
    request: Request | None,
) -> LeadActivity:
    when = occurred_at or datetime.now(UTC)
    activity = LeadActivity(
        id=uuid.uuid4(),
        lead_id=lead.id,
        activity_type=activity_type,
        summary=summary,
        performed_by=actor.id,
        occurred_at=when,
    )
    session.add(activity)
    if activity_type in CONTACT_ACTIVITY_TYPES:
        lead.last_contact_at = when
    await session.flush()

    if activity_type != "note":
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="lead.activity_logged",
            target_type="lead",
            target_id=lead.id,
            request=request,
            safe_metadata={"activity_type": activity_type},
        )
    return activity


async def schedule_follow_up(
    session: AsyncSession,
    *,
    actor: StaffUser,
    lead: Lead,
    scheduled_at: datetime,
    assigned_to: uuid.UUID,
    purpose: str | None,
    channel: str | None,
    request: Request | None,
) -> LeadFollowUp:
    if lead.do_not_contact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This lead is marked do-not-contact; no new follow-ups can be scheduled.",
        )

    follow_up = LeadFollowUp(
        id=uuid.uuid4(),
        lead_id=lead.id,
        assigned_to=assigned_to,
        scheduled_at=scheduled_at,
        status="scheduled",
        purpose=purpose,
        channel=channel,
        created_by=actor.id,
    )
    session.add(follow_up)
    lead.next_follow_up_at = scheduled_at
    session.add(
        LeadActivity(
            id=uuid.uuid4(),
            lead_id=lead.id,
            activity_type="follow_up_created",
            summary=f"Follow-up scheduled for {scheduled_at.isoformat()}.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.followup_scheduled",
        target_type="lead",
        target_id=lead.id,
        request=request,
        safe_metadata={"follow_up_id": str(follow_up.id), "scheduled_at": scheduled_at.isoformat()},
    )
    return follow_up


async def complete_follow_up(
    session: AsyncSession,
    *,
    actor: StaffUser,
    lead: Lead,
    follow_up: LeadFollowUp,
    outcome: str | None,
    request: Request | None,
) -> LeadFollowUp:
    follow_up.status = "completed"
    follow_up.completed_at = datetime.now(UTC)
    follow_up.completed_by = actor.id
    follow_up.outcome = outcome
    follow_up.updated_by = actor.id

    lead.last_contact_at = datetime.now(UTC)
    remaining = await session.scalar(
        select(LeadFollowUp.id).where(
            LeadFollowUp.lead_id == lead.id,
            LeadFollowUp.status.in_(("scheduled", "due")),
            LeadFollowUp.id != follow_up.id,
        )
    )
    if not remaining:
        lead.next_follow_up_at = None

    session.add(
        LeadActivity(
            id=uuid.uuid4(),
            lead_id=lead.id,
            activity_type="follow_up_completed",
            summary=outcome or "Follow-up completed.",
            performed_by=actor.id,
            occurred_at=datetime.now(UTC),
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.followup_completed",
        target_type="lead",
        target_id=lead.id,
        request=request,
        safe_metadata={"follow_up_id": str(follow_up.id)},
    )
    return follow_up


async def reschedule_follow_up(
    session: AsyncSession,
    *,
    actor: StaffUser,
    lead: Lead,
    follow_up: LeadFollowUp,
    scheduled_at: datetime,
    reason: str | None,
    request: Request | None,
) -> LeadFollowUp:
    before = follow_up.scheduled_at
    follow_up.scheduled_at = scheduled_at
    follow_up.status = "scheduled"
    follow_up.updated_by = actor.id
    lead.next_follow_up_at = scheduled_at
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.followup_rescheduled",
        target_type="lead",
        target_id=lead.id,
        request=request,
        before_summary={"scheduled_at": before.isoformat()},
        after_summary={"scheduled_at": scheduled_at.isoformat()},
        safe_metadata={"reason": reason, "follow_up_id": str(follow_up.id)},
    )
    return follow_up


async def preview_conversion(session: AsyncSession, *, lead: Lead) -> dict[str, Any]:
    matches = await _find_customer_matches(session, lead=lead)
    return {
        "possible_customer_matches": [c for c, _ in matches],
        "will_create_new_customer": not matches,
    }


async def _find_customer_matches(
    session: AsyncSession, *, lead: Lead
) -> list[tuple[Customer, list[str]]]:
    conditions = []
    if lead.phone_e164:
        conditions.append(Customer.primary_phone_e164 == lead.phone_e164)
    if lead.email:
        conditions.append(Customer.primary_email == lead.email)
    if not conditions:
        return []
    stmt = select(Customer).where(or_(*conditions), Customer.deleted_at.is_(None))
    candidates = (await session.scalars(stmt)).all()
    results = []
    for candidate in candidates:
        reasons = []
        if lead.phone_e164 and candidate.primary_phone_e164 == lead.phone_e164:
            reasons.append("exact_normalized_phone")
        if lead.email and candidate.primary_email == lead.email:
            reasons.append("exact_normalized_email")
        results.append((candidate, reasons))
    return results


async def execute_conversion(
    session: AsyncSession,
    *,
    actor: StaffUser,
    lead: Lead,
    existing_customer_id: uuid.UUID | None,
    idempotency_key: str,
    request: Request | None,
) -> Customer:
    if lead.status == "won" and lead.won_customer_id is not None:
        # Idempotent: a repeated call (same or different key) against an
        # already-converted lead returns the existing result rather than
        # converting again.
        existing = await session.get(Customer, lead.won_customer_id)
        if existing is not None:
            return existing

    existing_by_key = await session.scalar(
        select(Lead).where(Lead.conversion_idempotency_key == idempotency_key, Lead.id != lead.id)
    )
    if existing_by_key is not None and existing_by_key.won_customer_id is not None:
        result = await session.get(Customer, existing_by_key.won_customer_id)
        if result is not None:
            return result

    if lead.status in ("lost", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot convert a lead in '{lead.status}' status.",
        )

    if existing_customer_id is not None:
        customer = await session.get(Customer, existing_customer_id)
        if customer is None or customer.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    else:
        display_name = derive_display_name(
            display_name=lead.organization_name or lead.contact_name or lead.display_name,
            first_name=None,
            last_name=None,
            organization_name=lead.organization_name,
        )
        customer = Customer(
            id=uuid.uuid4(),
            customer_number=generate_customer_number(),
            customer_type="corporate" if lead.organization_name else "individual",
            organization_name=lead.organization_name,
            display_name=display_name,
            primary_phone_e164=lead.phone_e164,
            primary_email=lead.email,
            customer_status="active",
            customer_segment="new",
            acquisition_source=lead.source,
            assigned_staff_id=lead.assigned_staff_id,
            created_by=actor.id,
            last_activity_at=datetime.now(UTC),
        )
        session.add(customer)
        await session.flush()
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="customer.created",
            target_type="customer",
            target_id=customer.id,
            request=request,
            safe_metadata={
                "customer_number": customer.customer_number,
                "source_lead_id": str(lead.id),
            },
        )
        await record_domain_event(
            session,
            event_type="customer.created",
            aggregate_type="customer",
            aggregate_id=customer.id,
            payload={"customer_id": str(customer.id), "source_lead_id": str(lead.id)},
        )

    previous_status = lead.status
    now = datetime.now(UTC)
    lead.status = "won"
    lead.won_customer_id = customer.id
    lead.converted_at = now
    lead.converted_by = actor.id
    lead.conversion_idempotency_key = idempotency_key
    lead.updated_by = actor.id
    lead.version += 1

    session.add(
        LeadStatusHistory(
            id=uuid.uuid4(),
            lead_id=lead.id,
            previous_status=previous_status,
            new_status="won",
            actor_id=actor.id,
            reason="Converted to customer.",
        )
    )
    session.add(
        LeadActivity(
            id=uuid.uuid4(),
            lead_id=lead.id,
            activity_type="customer_conversion",
            summary=f"Converted to customer {customer.customer_number}.",
            performed_by=actor.id,
            occurred_at=now,
        )
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="lead.converted",
        target_type="lead",
        target_id=lead.id,
        request=request,
        safe_metadata={
            "customer_id": str(customer.id),
            "reused_existing_customer": existing_customer_id is not None,
        },
    )
    await record_domain_event(
        session,
        event_type="lead.stage_changed",
        aggregate_type="lead",
        aggregate_id=lead.id,
        payload={"lead_id": str(lead.id), "previous_status": previous_status, "new_status": "won"},
    )
    return customer
