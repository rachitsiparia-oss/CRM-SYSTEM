"""Service-layer workflow tests for complaints and the SLA engine —
`app.complaints.service`/`app.complaints.sla`. HTTP-layer permission
enforcement is covered by test_feedback_complaints_api.py; CHECK-constraint
correctness by test_feedback_complaints_models.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from app.complaints import service, sla
from app.complaints.errors import (
    DuplicateEscalationError,
    InvalidAssignmentError,
    InvalidStatusTransitionError,
    SelfLinkError,
    TransitionNotPermittedError,
)
from app.complaints.schemas import ComplaintCreateIn, SlaPolicyCreateIn, SlaPolicyUpdateIn
from app.db.models import BusinessHours, Complaint, Customer, StaffUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]
_IST = ZoneInfo("Asia/Kolkata")


async def _make_customer(session: AsyncSession, **overrides: object) -> Customer:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": "Test Customer",
        "first_name": "Test",
        "last_name": "Customer",
    }
    fields.update(overrides)
    customer = Customer(**fields)
    session.add(customer)
    await session.flush()
    return customer


async def _make_complaint_via_service(
    session: AsyncSession, *, actor: StaffUser, customer_id: uuid.UUID, **overrides: object
) -> Complaint:
    payload_fields: dict[str, object] = {
        "customer_id": customer_id,
        "source_type": "direct",
        "category": "delay",
        "title": "Order delivered late",
        "description": "Order arrived an hour late.",
        "severity": "medium",
        "priority": "normal",
    }
    payload_fields.update(overrides)
    return await service.create_complaint(
        session,
        actor=actor,
        payload=ComplaintCreateIn.model_validate(payload_fields),
    )


# --- State machine / assignment / notes / escalation ------------------------


async def test_complaint_transition_follows_state_machine(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint_via_service(db_session, actor=actor, customer_id=customer.id)

    with pytest.raises(InvalidStatusTransitionError):
        await service.transition_complaint(
            db_session, actor=actor, complaint=complaint, target_status="resolved"
        )

    complaint = await service.transition_complaint(
        db_session, actor=actor, complaint=complaint, target_status="acknowledged"
    )
    assert complaint.acknowledged_at is not None
    assert complaint.first_responded_at is not None


async def test_complaint_gated_resolve_requires_permission(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    """No seeded role holds `complaints.transition` without also holding
    `complaints.resolve` (every case-management role gets both together),
    so this builds a role carrying only the base transition grant directly
    from already-seeded `Permission` rows — the same technique
    `test_offers_api.py`'s `_make_role_with_permissions` uses to exercise a
    gated-target split no seeded role happens to isolate."""
    from app.db.models import Permission, Role, RolePermission, StaffRole

    limited_actor = await make_staff_user(role_code=None)
    role = Role(id=uuid.uuid4(), code=f"test-role-{uuid.uuid4().hex[:10]}", name="Test Role")
    db_session.add(role)
    await db_session.flush()
    codes = ["complaints.view", "complaints.create", "complaints.update", "complaints.transition"]
    permission_ids = await db_session.scalars(
        select(Permission.id).where(Permission.code.in_(codes))
    )
    for permission_id in permission_ids:
        db_session.add(
            RolePermission(role_id=role.id, permission_id=permission_id, scope_type="all")
        )
    db_session.add(StaffRole(staff_user_id=limited_actor.id, role_id=role.id))
    await db_session.flush()

    customer = await _make_customer(db_session)
    complaint = await _make_complaint_via_service(
        db_session, actor=limited_actor, customer_id=customer.id
    )
    complaint = await service.transition_complaint(
        db_session,
        actor=limited_actor,
        complaint=complaint,
        target_status="investigating",
    )
    complaint = await service.transition_complaint(
        db_session,
        actor=limited_actor,
        complaint=complaint,
        target_status="resolution_proposed",
    )
    with pytest.raises(TransitionNotPermittedError):
        await service.transition_complaint(
            db_session, actor=limited_actor, complaint=complaint, target_status="resolved"
        )


async def test_complaint_reopen_resets_resolution_timestamps(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint_via_service(db_session, actor=actor, customer_id=customer.id)
    complaint = await service.transition_complaint(
        db_session, actor=actor, complaint=complaint, target_status="investigating"
    )
    complaint = await service.transition_complaint(
        db_session, actor=actor, complaint=complaint, target_status="resolution_proposed"
    )
    complaint = await service.transition_complaint(
        db_session, actor=actor, complaint=complaint, target_status="resolved"
    )
    assert complaint.resolved_at is not None

    complaint = await service.transition_complaint(
        db_session, actor=actor, complaint=complaint, target_status="reopened"
    )
    assert complaint.resolved_at is None
    assert complaint.reopened_count == 1
    assert complaint.status == "reopened"


async def test_complaint_assignment_requires_staff_or_department(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint_via_service(db_session, actor=actor, customer_id=customer.id)
    with pytest.raises(InvalidAssignmentError):
        await service.assign_complaint(
            db_session,
            actor=actor,
            complaint=complaint,
            assigned_staff_id=None,
            assigned_department_id=None,
        )

    complaint = await service.assign_complaint(
        db_session,
        actor=actor,
        complaint=complaint,
        assigned_staff_id=actor.id,
        assigned_department_id=None,
        reason="Self-assigned for triage.",
    )
    assert complaint.assigned_staff_id == actor.id


async def test_complaint_escalation_is_deduplicated(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint_via_service(db_session, actor=actor, customer_id=customer.id)
    escalation = await service.escalate_complaint(
        db_session, actor=actor, complaint=complaint, reason="No response within SLA."
    )
    assert escalation.level == 1
    assert complaint.current_escalation_level == 1

    # Simulates a retried request racing against the first one — both read
    # `current_escalation_level == 0` before either write landed, so both
    # target level 1; the second must be rejected by the dedup_key rather
    # than silently creating a second level-1 escalation row.
    complaint.current_escalation_level = 0
    with pytest.raises(DuplicateEscalationError):
        await service.escalate_complaint(
            db_session, actor=actor, complaint=complaint, reason="Retried escalation."
        )


async def test_complaint_link_rejects_self_link_via_service(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint_via_service(db_session, actor=actor, customer_id=customer.id)
    with pytest.raises(SelfLinkError):
        await service.link_complaint(
            db_session,
            actor=actor,
            complaint=complaint,
            related_complaint_id=complaint.id,
            relationship_type="related_to",
        )


async def test_follow_up_escalated_again_outcome_triggers_new_escalation(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint_via_service(db_session, actor=actor, customer_id=customer.id)
    follow_up = await service.schedule_follow_up(
        db_session,
        actor=actor,
        complaint=complaint,
        scheduled_at=datetime.now(UTC) + timedelta(days=1),
    )
    await service.complete_follow_up(
        db_session,
        actor=actor,
        follow_up=follow_up,
        outcome="escalated_again",
        notes="Customer still unhappy.",
    )
    assert complaint.current_escalation_level == 1


async def test_build_timeline_aggregates_across_tables(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint_via_service(db_session, actor=actor, customer_id=customer.id)
    await service.assign_complaint(
        db_session,
        actor=actor,
        complaint=complaint,
        assigned_staff_id=actor.id,
        assigned_department_id=None,
    )
    await service.add_note(db_session, actor=actor, complaint=complaint, note="Investigating.")
    await service.transition_complaint(
        db_session, actor=actor, complaint=complaint, target_status="acknowledged"
    )

    timeline = await service.build_timeline(db_session, complaint.id)
    entry_types = {entry["entry_type"] for entry in timeline}
    assert {"status_change", "assignment", "note"} <= entry_types
    occurred_ats = [entry["occurred_at"] for entry in timeline]
    assert occurred_ats == sorted(occurred_ats)


# --- SLA engine --------------------------------------------------------------


async def test_compute_due_at_without_business_hours_is_simple_addition(
    db_session: AsyncSession,
) -> None:
    base_time = datetime(2024, 6, 10, 12, 0, tzinfo=UTC)
    due_at = await sla.compute_due_at(
        db_session, base_time=base_time, minutes=90, business_hours_only=False
    )
    assert due_at == base_time + timedelta(minutes=90)


async def test_compute_due_at_skips_to_next_business_day(db_session: AsyncSession) -> None:
    """Monday 21:30 IST + 90 minutes, with 09:00-22:00 hours both days,
    must land at Tuesday 10:00 IST (30 min left in Monday's window, the
    remaining 60 rolling into Tuesday's open)."""
    monday_row = await db_session.scalar(
        select(BusinessHours).where(BusinessHours.day_of_week == 0)
    )
    tuesday_row = await db_session.scalar(
        select(BusinessHours).where(BusinessHours.day_of_week == 1)
    )
    assert monday_row is not None and tuesday_row is not None
    for row in (monday_row, tuesday_row):
        row.is_closed = False
        row.opens_at = datetime(2000, 1, 1, 9, 0).time()
        row.closes_at = datetime(2000, 1, 1, 22, 0).time()
        row.closes_next_day = False
    await db_session.flush()

    base_time = datetime(2024, 1, 1, 21, 30, tzinfo=_IST).astimezone(UTC)  # a Monday
    due_at = await sla.compute_due_at(
        db_session, base_time=base_time, minutes=90, business_hours_only=True
    )
    expected = datetime(2024, 1, 2, 10, 0, tzinfo=_IST).astimezone(UTC)
    assert due_at == expected


async def test_select_sla_policy_prefers_more_specific_match(db_session: AsyncSession) -> None:
    general = await sla.create_sla_policy(
        db_session,
        payload=SlaPolicyCreateIn(
            code=f"general-{uuid.uuid4().hex[:8]}",
            name="General policy",
            first_response_minutes=120,
            acknowledgement_minutes=240,
            resolution_minutes=2880,
        ),
    )
    specific = await sla.create_sla_policy(
        db_session,
        payload=SlaPolicyCreateIn(
            code=f"specific-{uuid.uuid4().hex[:8]}",
            name="Critical delay policy",
            applicable_categories=["delay"],
            applicable_severities=["critical"],
            first_response_minutes=15,
            acknowledgement_minutes=30,
            resolution_minutes=240,
        ),
    )
    selected = await sla.select_sla_policy(db_session, category="delay", severity="critical")
    assert selected is not None
    assert selected.id == specific.id
    assert selected.id != general.id


async def test_apply_sla_to_complaint_sets_due_dates_when_policy_matches(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    await sla.create_sla_policy(
        db_session,
        payload=SlaPolicyCreateIn(
            code=f"catchall-{uuid.uuid4().hex[:8]}",
            name="Catch-all policy",
            first_response_minutes=60,
            acknowledgement_minutes=120,
            resolution_minutes=1440,
            business_hours_only=False,
        ),
    )
    complaint = await _make_complaint_via_service(db_session, actor=actor, customer_id=customer.id)
    assert complaint.sla_policy_id is not None
    assert complaint.first_response_due_at is not None
    assert complaint.resolution_due_at is not None


async def test_detect_sla_events_is_idempotent(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    policy = await sla.create_sla_policy(
        db_session,
        payload=SlaPolicyCreateIn(
            code=f"breach-{uuid.uuid4().hex[:8]}",
            name="Breach policy",
            first_response_minutes=1,
            acknowledgement_minutes=1,
            resolution_minutes=1,
            business_hours_only=False,
        ),
    )
    complaint = await _make_complaint_via_service(
        db_session, actor=actor, customer_id=customer.id, sla_policy_id=policy.id
    )
    # Force the due-at fields into the past so `detect_sla_events` sees an
    # already-breached complaint deterministically.
    past = datetime.now(UTC) - timedelta(hours=2)
    complaint.first_response_due_at = past
    complaint.acknowledgement_due_at = past
    complaint.resolution_due_at = past
    await db_session.flush()

    first_pass = await sla.detect_sla_events(db_session)
    assert len(first_pass) >= 1

    second_pass = await sla.detect_sla_events(db_session)
    assert second_pass == []


async def test_run_sla_escalations_creates_task_and_escalates(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    policy = await sla.create_sla_policy(
        db_session,
        payload=SlaPolicyCreateIn(
            code=f"autoescalate-{uuid.uuid4().hex[:8]}",
            name="Auto-escalate policy",
            first_response_minutes=1,
            acknowledgement_minutes=1,
            resolution_minutes=1,
            escalation_after_minutes=1,
            business_hours_only=False,
        ),
    )
    complaint = await _make_complaint_via_service(
        db_session, actor=actor, customer_id=customer.id, sla_policy_id=policy.id
    )
    past = datetime.now(UTC) - timedelta(hours=2)
    complaint.resolution_due_at = past
    await db_session.flush()

    escalations = await service.run_sla_escalations(db_session)
    assert len(escalations) == 1
    assert complaint.current_escalation_level == 1


async def test_get_sla_policy_returns_none_when_missing(db_session: AsyncSession) -> None:
    assert await sla.get_sla_policy(db_session, uuid.uuid4()) is None


async def test_update_sla_policy_applies_partial_update(db_session: AsyncSession) -> None:
    policy = await sla.create_sla_policy(
        db_session,
        payload=SlaPolicyCreateIn(
            code=f"update-{uuid.uuid4().hex[:8]}",
            name="Updatable policy",
            first_response_minutes=60,
            acknowledgement_minutes=120,
            resolution_minutes=1440,
        ),
    )
    updated = await sla.update_sla_policy(
        db_session, policy=policy, payload=SlaPolicyUpdateIn(is_active=False)
    )
    assert updated.is_active is False
    assert updated.name == "Updatable policy"
