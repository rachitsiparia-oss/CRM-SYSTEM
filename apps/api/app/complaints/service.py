"""Complaint state machine, assignment, notes, escalation, follow-ups,
links, and read-time timeline aggregation —
GROWTH_AND_INTELLIGENCE.md section 12.3-12.9."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.complaints import sla
from app.complaints.errors import (
    DuplicateEscalationError,
    InvalidAssignmentError,
    InvalidStatusTransitionError,
    SelfLinkError,
)
from app.complaints.schemas import ComplaintCreateIn, ComplaintStatus, ComplaintUpdateIn
from app.db.models import (
    Complaint,
    ComplaintAssignment,
    ComplaintEscalation,
    ComplaintFollowUp,
    ComplaintLink,
    ComplaintNote,
    ComplaintRootCauseHistory,
    ComplaintStatusHistory,
    Role,
    StaffRole,
    StaffUser,
)
from app.notifications.service import notify

# GROWTH_AND_INTELLIGENCE.md section 12.3's lifecycle, plus `cancelled`
# (see the `Complaint` model's own docstring for why it's a documented
# addition, not a contradiction). `reopened` re-enters the working set at
# `investigating`; `resolved`/`closed`/`cancelled` are the only terminal
# states this dict has no outbound edges for.
_COMPLAINT_TRANSITIONS: dict[str, set[str]] = {
    "new": {"acknowledged", "investigating", "cancelled"},
    "acknowledged": {"investigating", "awaiting_customer", "awaiting_internal", "cancelled"},
    "investigating": {
        "awaiting_customer",
        "awaiting_internal",
        "resolution_proposed",
        "cancelled",
    },
    "awaiting_customer": {"investigating", "resolution_proposed", "cancelled"},
    "awaiting_internal": {"investigating", "resolution_proposed", "cancelled"},
    "resolution_proposed": {"investigating", "resolved", "cancelled"},
    "resolved": {"closed", "reopened"},
    "closed": {"reopened"},
    "reopened": {"investigating", "acknowledged"},
    "cancelled": set(),
}

# A transition into these targets needs a permission beyond the base
# `complaints.transition` grant — checked by the router, the same
# router-level special-case pattern `app.offers.router` uses for
# `offers.approve`. Kept here as the single source of the mapping so the
# router doesn't hardcode it.
GATED_TRANSITIONS: dict[str, str] = {
    "resolved": "complaints.resolve",
    "closed": "complaints.close",
    "reopened": "complaints.reopen",
}


def generate_complaint_number() -> str:
    return f"CMP-{uuid.uuid4().hex[:8].upper()}"


async def _notify_management(
    session: AsyncSession,
    *,
    notification_type: str,
    title: str,
    body: str | None,
    priority: str,
    record_type: str,
    record_id: uuid.UUID,
    dedup_key: str,
) -> None:
    """CORE_CRM_MODULES.md section 11's notification matrix ("High-severity
    complaint -> general manager") names a role, not a specific staff
    member — there is no existing "notify everyone holding role X" helper
    anywhere in the codebase, so this fans a single `notify()` call for
    each active owner/general_manager out individually. `dedup_key` is
    suffixed per-recipient so one recipient's existing notification doesn't
    silently suppress another's."""
    recipients = await session.scalars(
        select(StaffUser.id)
        .join(StaffRole, StaffRole.staff_user_id == StaffUser.id)
        .join(Role, Role.id == StaffRole.role_id)
        .where(
            Role.code.in_(["owner", "general_manager"]),
            StaffUser.account_status == "active",
            StaffUser.deleted_at.is_(None),
        )
        .distinct()
    )
    for recipient_id in recipients.all():
        await notify(
            session,
            notification_type=notification_type,
            title=title,
            recipient_staff_id=recipient_id,
            body=body,
            priority=priority,
            record_type=record_type,
            record_id=record_id,
            dedup_key=f"{dedup_key}:{recipient_id}",
        )


async def get_complaint(session: AsyncSession, complaint_id: uuid.UUID) -> Complaint | None:
    return await session.get(Complaint, complaint_id)


async def list_complaints(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    assigned_staff_id: uuid.UUID | None = None,
    assigned_department_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    scope_staff_id: uuid.UUID | None = None,
) -> tuple[list[Complaint], int]:
    """`scope_staff_id` restricts results to complaints assigned to that
    staff member — set by the router when the actor holds `complaints.view`
    but not `complaints.view_all`."""
    query = select(Complaint)
    if status:
        query = query.where(Complaint.status == status)
    if severity:
        query = query.where(Complaint.severity == severity)
    if category:
        query = query.where(Complaint.category == category)
    if assigned_staff_id:
        query = query.where(Complaint.assigned_staff_id == assigned_staff_id)
    if assigned_department_id:
        query = query.where(Complaint.assigned_department_id == assigned_department_id)
    if customer_id:
        query = query.where(Complaint.customer_id == customer_id)
    if scope_staff_id:
        query = query.where(Complaint.assigned_staff_id == scope_staff_id)

    from sqlalchemy import func

    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    query = (
        query.order_by(Complaint.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = list((await session.scalars(query)).all())
    return rows, total or 0


async def create_complaint(
    session: AsyncSession, *, actor: StaffUser | None, payload: ComplaintCreateIn
) -> Complaint:
    complaint = Complaint(
        complaint_number=generate_complaint_number(),
        customer_id=payload.customer_id,
        source_type=payload.source_type,
        feedback_id=payload.feedback_id,
        conversation_id=payload.conversation_id,
        order_id=payload.order_id,
        reservation_id=payload.reservation_id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        priority=payload.priority,
        channel=payload.channel,
        is_hr_sensitive=payload.category == "staff_behavior",
        created_by=actor.id if actor else None,
        updated_by=actor.id if actor else None,
    )
    session.add(complaint)
    await session.flush()

    if payload.sla_policy_id is not None:
        from app.db.models import SlaPolicy

        policy = await session.get(SlaPolicy, payload.sla_policy_id)
        if policy is not None:
            complaint.sla_policy_id = policy.id
            complaint.first_response_due_at = await sla.compute_due_at(
                session,
                base_time=complaint.created_at,
                minutes=policy.first_response_minutes,
                business_hours_only=policy.business_hours_only,
            )
            complaint.acknowledgement_due_at = await sla.compute_due_at(
                session,
                base_time=complaint.created_at,
                minutes=policy.acknowledgement_minutes,
                business_hours_only=policy.business_hours_only,
            )
            complaint.resolution_due_at = await sla.compute_due_at(
                session,
                base_time=complaint.created_at,
                minutes=policy.resolution_minutes,
                business_hours_only=policy.business_hours_only,
            )
    else:
        await sla.apply_sla_to_complaint(session, complaint=complaint)

    session.add(
        ComplaintStatusHistory(
            complaint_id=complaint.id,
            from_status=None,
            to_status="new",
            actor_id=actor.id if actor else None,
        )
    )
    await session.flush()

    if actor is not None:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="complaint.created",
            target_type="complaint",
            target_id=complaint.id,
            safe_metadata={"category": payload.category, "severity": payload.severity},
        )

    if complaint.severity in ("high", "critical"):
        severity_label = complaint.severity.capitalize()
        await _notify_management(
            session,
            notification_type="complaint.high_severity",
            title=f"{severity_label} severity complaint {complaint.complaint_number}",
            body=complaint.title,
            priority="urgent" if complaint.severity == "critical" else "high",
            record_type="complaint",
            record_id=complaint.id,
            dedup_key=f"complaint.high_severity:{complaint.id}",
        )
    return complaint


async def update_complaint(
    session: AsyncSession, *, actor: StaffUser, complaint: Complaint, payload: ComplaintUpdateIn
) -> Complaint:
    if payload.title is not None:
        complaint.title = payload.title
    if payload.description is not None:
        complaint.description = payload.description
    if payload.category is not None:
        complaint.category = payload.category
        complaint.is_hr_sensitive = payload.category == "staff_behavior"
    if payload.severity is not None:
        complaint.severity = payload.severity
    if payload.priority is not None:
        complaint.priority = payload.priority
    if payload.customer_visible_summary is not None:
        complaint.customer_visible_summary = payload.customer_visible_summary
    complaint.updated_by = actor.id
    await session.flush()
    return complaint


async def transition_complaint(
    session: AsyncSession,
    *,
    actor: StaffUser,
    complaint: Complaint,
    target_status: ComplaintStatus,
    reason: str | None = None,
    resolution_summary: str | None = None,
) -> Complaint:
    allowed = _COMPLAINT_TRANSITIONS.get(complaint.status, set())
    if target_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition complaint from {complaint.status!r} to {target_status!r}."
        )

    now = datetime.now(UTC)
    from_status = complaint.status
    complaint.status = target_status
    complaint.updated_by = actor.id

    if target_status == "acknowledged" and complaint.acknowledged_at is None:
        complaint.acknowledged_at = now
    if complaint.first_responded_at is None and target_status not in ("new",):
        complaint.first_responded_at = now
    if target_status == "resolved":
        complaint.resolved_at = now
        if resolution_summary is not None:
            complaint.resolution_summary = resolution_summary
    if target_status == "closed":
        complaint.closed_at = now
    if target_status == "reopened":
        complaint.reopened_at = now
        complaint.reopened_count += 1
        complaint.resolved_at = None
        complaint.closed_at = None

    session.add(
        ComplaintStatusHistory(
            complaint_id=complaint.id,
            from_status=from_status,
            to_status=target_status,
            actor_id=actor.id,
            reason=reason,
        )
    )
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="complaint.transitioned",
        target_type="complaint",
        target_id=complaint.id,
        safe_metadata={"from_status": from_status, "to_status": target_status},
    )

    if target_status == "reopened":
        await notify(
            session,
            notification_type="complaint.reopened",
            title=f"Complaint {complaint.complaint_number} reopened",
            recipient_staff_id=complaint.assigned_staff_id or actor.id,
            priority="high",
            record_type="complaint",
            record_id=complaint.id,
            dedup_key=f"complaint.reopened:{complaint.id}:{complaint.reopened_count}",
        )
    return complaint


async def assign_complaint(
    session: AsyncSession,
    *,
    actor: StaffUser,
    complaint: Complaint,
    assigned_staff_id: uuid.UUID | None,
    assigned_department_id: uuid.UUID | None,
    reason: str | None = None,
) -> Complaint:
    if assigned_staff_id is None and assigned_department_id is None:
        raise InvalidAssignmentError("An assignment requires a staff member or a department.")

    complaint.assigned_staff_id = assigned_staff_id
    complaint.assigned_department_id = assigned_department_id
    complaint.updated_by = actor.id
    session.add(
        ComplaintAssignment(
            complaint_id=complaint.id,
            assigned_staff_id=assigned_staff_id,
            assigned_department_id=assigned_department_id,
            assigned_by=actor.id,
            reason=reason,
        )
    )
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="complaint.assigned",
        target_type="complaint",
        target_id=complaint.id,
        safe_metadata={
            "assigned_staff_id": str(assigned_staff_id) if assigned_staff_id else None,
            "assigned_department_id": str(assigned_department_id)
            if assigned_department_id
            else None,
        },
    )
    if assigned_staff_id is not None:
        await notify(
            session,
            notification_type="complaint.assigned",
            title=f"Complaint {complaint.complaint_number} assigned to you",
            recipient_staff_id=assigned_staff_id,
            body=complaint.title,
            priority="high" if complaint.severity in ("high", "critical") else "normal",
            record_type="complaint",
            record_id=complaint.id,
            dedup_key=f"complaint.assigned:{complaint.id}:{assigned_staff_id}",
        )
    return complaint


async def escalate_complaint(
    session: AsyncSession,
    *,
    actor: StaffUser | None,
    complaint: Complaint,
    reason: str,
    new_assigned_staff_id: uuid.UUID | None = None,
    new_assigned_department_id: uuid.UUID | None = None,
) -> ComplaintEscalation:
    next_level = complaint.current_escalation_level + 1
    dedup_key = f"complaint:{complaint.id}:level:{next_level}"
    existing = await session.scalar(
        select(ComplaintEscalation.id).where(ComplaintEscalation.dedup_key == dedup_key)
    )
    if existing is not None:
        raise DuplicateEscalationError(
            f"Complaint {complaint.complaint_number} was already escalated to level {next_level}."
        )

    previous_staff_id = complaint.assigned_staff_id
    previous_department_id = complaint.assigned_department_id
    escalation = ComplaintEscalation(
        complaint_id=complaint.id,
        level=next_level,
        reason=reason,
        triggered_by_staff_id=actor.id if actor else None,
        previous_assigned_staff_id=previous_staff_id,
        previous_assigned_department_id=previous_department_id,
        new_assigned_staff_id=new_assigned_staff_id,
        new_assigned_department_id=new_assigned_department_id,
        dedup_key=dedup_key,
    )
    session.add(escalation)
    complaint.current_escalation_level = next_level
    if new_assigned_staff_id is not None or new_assigned_department_id is not None:
        complaint.assigned_staff_id = new_assigned_staff_id
        complaint.assigned_department_id = new_assigned_department_id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id if actor else None,
        action_code="complaint.escalated",
        target_type="complaint",
        target_id=complaint.id,
        safe_metadata={"level": next_level, "reason": reason},
    )
    if new_assigned_staff_id is not None:
        await notify(
            session,
            notification_type="complaint.escalated",
            title=f"Complaint {complaint.complaint_number} escalated to you (level {next_level})",
            recipient_staff_id=new_assigned_staff_id,
            body=reason,
            priority="urgent",
            record_type="complaint",
            record_id=complaint.id,
            dedup_key=f"complaint.escalated.notify:{complaint.id}:{next_level}",
        )
    return escalation


async def update_root_cause(
    session: AsyncSession,
    *,
    actor: StaffUser,
    complaint: Complaint,
    root_cause: str,
    notes: str | None = None,
) -> Complaint:
    from_root_cause = complaint.root_cause
    complaint.root_cause = root_cause
    complaint.updated_by = actor.id
    session.add(
        ComplaintRootCauseHistory(
            complaint_id=complaint.id,
            from_root_cause=from_root_cause,
            to_root_cause=root_cause,
            actor_id=actor.id,
            notes=notes,
        )
    )
    await session.flush()
    return complaint


async def add_note(
    session: AsyncSession, *, actor: StaffUser, complaint: Complaint, note: str
) -> ComplaintNote:
    row = ComplaintNote(complaint_id=complaint.id, author_staff_id=actor.id, note=note)
    session.add(row)
    await session.flush()
    return row


async def schedule_follow_up(
    session: AsyncSession,
    *,
    actor: StaffUser,
    complaint: Complaint,
    scheduled_at: datetime,
    notes: str | None = None,
) -> ComplaintFollowUp:
    row = ComplaintFollowUp(
        complaint_id=complaint.id, scheduled_at=scheduled_at, notes=notes, created_by=actor.id
    )
    session.add(row)
    complaint.follow_up_due_at = scheduled_at
    await session.flush()
    return row


async def complete_follow_up(
    session: AsyncSession,
    *,
    actor: StaffUser,
    follow_up: ComplaintFollowUp,
    outcome: str,
    notes: str | None = None,
) -> ComplaintFollowUp:
    follow_up.completed_at = datetime.now(UTC)
    follow_up.outcome = outcome
    if notes is not None:
        follow_up.notes = notes
    await session.flush()
    if outcome == "escalated_again":
        complaint = await get_complaint(session, follow_up.complaint_id)
        if complaint is not None:
            await escalate_complaint(
                session,
                actor=actor,
                complaint=complaint,
                reason="Follow-up outcome: escalated_again.",
            )
    return follow_up


async def link_complaint(
    session: AsyncSession,
    *,
    actor: StaffUser,
    complaint: Complaint,
    related_complaint_id: uuid.UUID,
    relationship_type: str,
) -> ComplaintLink:
    if related_complaint_id == complaint.id:
        raise SelfLinkError("A complaint cannot be linked to itself.")
    row = ComplaintLink(
        complaint_id=complaint.id,
        related_complaint_id=related_complaint_id,
        relationship_type=relationship_type,
        created_by=actor.id,
    )
    session.add(row)
    await session.flush()
    return row


async def build_timeline(session: AsyncSession, complaint_id: uuid.UUID) -> list[dict[str, Any]]:
    """Read-time aggregation across status/root-cause history, assignments,
    notes, escalations, and follow-ups — CLAUDE.md section 12.3's "Do not
    create a redundant generic timeline table"."""
    entries: list[dict[str, Any]] = []

    status_rows = (
        await session.scalars(
            select(ComplaintStatusHistory).where(
                ComplaintStatusHistory.complaint_id == complaint_id
            )
        )
    ).all()
    for status_row in status_rows:
        entries.append(
            {
                "entry_type": "status_change",
                "occurred_at": status_row.created_at,
                "actor_id": status_row.actor_id,
                "summary": f"Status changed to {status_row.to_status}",
                "detail": {
                    "from_status": status_row.from_status,
                    "to_status": status_row.to_status,
                    "reason": status_row.reason,
                },
            }
        )

    assignment_rows = (
        await session.scalars(
            select(ComplaintAssignment).where(ComplaintAssignment.complaint_id == complaint_id)
        )
    ).all()
    for assignment_row in assignment_rows:
        entries.append(
            {
                "entry_type": "assignment",
                "occurred_at": assignment_row.created_at,
                "actor_id": assignment_row.assigned_by,
                "summary": "Complaint assigned",
                "detail": {
                    "assigned_staff_id": str(assignment_row.assigned_staff_id)
                    if assignment_row.assigned_staff_id
                    else None,
                    "assigned_department_id": (
                        str(assignment_row.assigned_department_id)
                        if assignment_row.assigned_department_id
                        else None
                    ),
                },
            }
        )

    note_rows = (
        await session.scalars(
            select(ComplaintNote).where(ComplaintNote.complaint_id == complaint_id)
        )
    ).all()
    for note_row in note_rows:
        entries.append(
            {
                "entry_type": "note",
                "occurred_at": note_row.created_at,
                "actor_id": note_row.author_staff_id,
                "summary": "Note added",
                "detail": {"note": note_row.note},
            }
        )

    escalation_rows = (
        await session.scalars(
            select(ComplaintEscalation).where(ComplaintEscalation.complaint_id == complaint_id)
        )
    ).all()
    for escalation_row in escalation_rows:
        entries.append(
            {
                "entry_type": "escalation",
                "occurred_at": escalation_row.created_at,
                "actor_id": escalation_row.triggered_by_staff_id,
                "summary": f"Escalated to level {escalation_row.level}",
                "detail": {"reason": escalation_row.reason, "level": escalation_row.level},
            }
        )

    follow_up_rows = (
        await session.scalars(
            select(ComplaintFollowUp).where(ComplaintFollowUp.complaint_id == complaint_id)
        )
    ).all()
    for follow_up_row in follow_up_rows:
        entries.append(
            {
                "entry_type": "follow_up",
                "occurred_at": follow_up_row.created_at,
                "actor_id": follow_up_row.created_by,
                "summary": f"Follow-up scheduled for {follow_up_row.scheduled_at.isoformat()}",
                "detail": {"outcome": follow_up_row.outcome, "notes": follow_up_row.notes},
            }
        )

    entries.sort(key=lambda e: e["occurred_at"])
    return entries


async def run_sla_escalations(session: AsyncSession) -> list[ComplaintEscalation]:
    """Orchestrates `app.complaints.sla.detect_sla_events` and auto-
    escalates a complaint the first time a `breached_resolution` event with
    an `escalation_after_minutes`-configured policy is recorded for it —
    deterministic and idempotent (escalation itself dedups on
    `complaint:{id}:level:{level}`)."""
    events = await sla.detect_sla_events(session)
    escalations: list[ComplaintEscalation] = []
    for event in events:
        if event.event_type != "breached_resolution":
            continue
        complaint = await get_complaint(session, event.complaint_id)
        if complaint is None or complaint.sla_policy_id is None:
            continue
        from app.db.models import SlaPolicy

        policy = await session.get(SlaPolicy, complaint.sla_policy_id)
        if policy is None or policy.escalation_after_minutes is None:
            continue
        try:
            escalation = await escalate_complaint(
                session,
                actor=None,
                complaint=complaint,
                reason=f"Automatic escalation — SLA resolution target breached ({policy.name}).",
            )
            escalations.append(escalation)
        except DuplicateEscalationError:
            continue
    return escalations
