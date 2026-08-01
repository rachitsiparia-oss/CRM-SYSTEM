"""Service-layer workflow tests for service recovery —
`app.service_recovery.service`. HTTP-layer permission enforcement is
covered by test_feedback_complaints_api.py; CHECK-constraint correctness by
test_feedback_complaints_models.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.complaints import service as complaints_service
from app.complaints.schemas import ComplaintCreateIn
from app.db.models import Complaint, Customer, StaffUser
from app.service_recovery import service
from app.service_recovery.errors import (
    ApprovalNotRequiredError,
    InvalidActionStatusTransitionError,
    SelfApprovalNotAllowedError,
)
from app.service_recovery.schemas import ApprovalRuleCreateIn, ApprovalRuleUpdateIn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


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


async def _make_complaint(
    session: AsyncSession, *, actor: StaffUser, customer_id: uuid.UUID, severity: str = "medium"
) -> Complaint:
    return await complaints_service.create_complaint(
        session,
        actor=actor,
        payload=ComplaintCreateIn(
            customer_id=customer_id,
            source_type="direct",
            category="delay",
            title="Late order",
            description="Order arrived late.",
            severity=severity,  # type: ignore[arg-type]
            priority="normal",
        ),
    )


# --- Approval rule matching ---------------------------------------------


async def test_evaluate_approval_requirement_prefers_specific_rule(
    db_session: AsyncSession,
) -> None:
    await service.create_approval_rule(
        db_session,
        payload=ApprovalRuleCreateIn(
            code=f"general-{uuid.uuid4().hex[:8]}",
            name="General",
            required_permission="recovery.approve",
        ),
    )
    specific = await service.create_approval_rule(
        db_session,
        payload=ApprovalRuleCreateIn(
            code=f"specific-{uuid.uuid4().hex[:8]}",
            name="Specific discount rule",
            recovery_type="discount",
            min_value_minor=5_000,
            applicable_severities=["high", "critical"],
            required_permission="recovery.approve",
        ),
    )
    matched = await service.evaluate_approval_requirement(
        db_session, recovery_type="discount", value_minor=10_000, points=None, severity="high"
    )
    assert matched is not None
    assert matched.id == specific.id


async def test_evaluate_approval_requirement_returns_none_when_no_rule_matches(
    db_session: AsyncSession,
) -> None:
    matched = await service.evaluate_approval_requirement(
        db_session, recovery_type="apology_only", value_minor=None, points=None, severity="low"
    )
    assert matched is None


# --- Propose / approve / reject ---------------------------------------------


async def test_propose_action_self_service_when_no_rule_matches(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="apology_only",
        value_minor=None,
        points=None,
        description="Formal apology call.",
    )
    assert action.approval_required is False
    assert action.status == "proposed"


async def test_propose_action_requires_approval_when_rule_matches(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    await service.create_approval_rule(
        db_session,
        payload=ApprovalRuleCreateIn(
            code=f"high-value-{uuid.uuid4().hex[:8]}",
            name="High value",
            recovery_type="discount",
            min_value_minor=1_000,
            applicable_severities=["high", "critical"],
            required_permission="recovery.approve",
        ),
    )
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(
        db_session, actor=actor, customer_id=customer.id, severity="high"
    )
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="discount",
        value_minor=5_000,
        points=None,
        description="₹50 discount for the delay.",
    )
    assert action.approval_required is True
    assert action.status == "approval_required"
    assert action.approval_rule_id is not None


async def test_approve_action_blocks_self_approval_unless_rule_allows(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    await service.create_approval_rule(
        db_session,
        payload=ApprovalRuleCreateIn(
            code=f"no-self-approve-{uuid.uuid4().hex[:8]}",
            name="No self approve",
            recovery_type="discount",
            min_value_minor=1_000,
            required_permission="recovery.approve",
            allow_self_approval=False,
        ),
    )
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="discount",
        value_minor=5_000,
        points=None,
        description="₹50 discount.",
    )
    with pytest.raises(SelfApprovalNotAllowedError):
        await service.approve_action(db_session, actor=actor, action=action)


async def test_approve_action_allowed_when_rule_allows_self_approval(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    await service.create_approval_rule(
        db_session,
        payload=ApprovalRuleCreateIn(
            code=f"allow-self-{uuid.uuid4().hex[:8]}",
            name="Allow self approve",
            recovery_type="discount",
            min_value_minor=1_000,
            required_permission="recovery.approve",
            allow_self_approval=True,
        ),
    )
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="discount",
        value_minor=5_000,
        points=None,
        description="₹50 discount.",
    )
    approved = await service.approve_action(db_session, actor=actor, action=action)
    assert approved.status == "approved"
    assert approved.approved_by_staff_id == actor.id


async def test_approve_action_rejects_when_not_pending_approval(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="apology_only",
        value_minor=None,
        points=None,
        description="Apology.",
    )
    with pytest.raises(ApprovalNotRequiredError):
        await service.approve_action(db_session, actor=actor, action=action)


async def test_reject_action_records_reason(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    approver = await make_staff_user(role_code="owner")
    await service.create_approval_rule(
        db_session,
        payload=ApprovalRuleCreateIn(
            code=f"reject-{uuid.uuid4().hex[:8]}",
            name="Reject test rule",
            recovery_type="discount",
            min_value_minor=1_000,
            required_permission="recovery.approve",
        ),
    )
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="discount",
        value_minor=5_000,
        points=None,
        description="₹50 discount.",
    )
    rejected = await service.reject_action(
        db_session, actor=approver, action=action, reason="Value too high for this incident."
    )
    assert rejected.status == "rejected"
    assert rejected.rejected_reason == "Value too high for this incident."


# --- Execute / reverse ---------------------------------------------------


async def test_execute_action_loyalty_credit_posts_ledger_entry_and_updates_segment(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="loyalty_credit",
        value_minor=None,
        points=150,
        description="150 bonus points.",
    )
    executed = await service.execute_action(db_session, actor=actor, action=action)
    assert executed.status == "completed"
    assert executed.execution_reference_type == "loyalty_ledger_entry"
    assert executed.execution_reference_id is not None
    await db_session.flush()
    await db_session.refresh(customer)
    assert customer.customer_segment == "complaint_recovery"


async def test_execute_action_manual_type_records_manual_reference(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="apology_only",
        value_minor=None,
        points=None,
        description="Formal apology.",
    )
    executed = await service.execute_action(db_session, actor=actor, action=action)
    assert executed.status == "completed"
    assert executed.execution_reference_type == "manual"
    assert executed.execution_reference_id is None


async def test_execute_action_rejects_already_completed(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="apology_only",
        value_minor=None,
        points=None,
        description="Formal apology.",
    )
    await service.execute_action(db_session, actor=actor, action=action)
    from app.service_recovery.errors import AlreadyExecutedError

    with pytest.raises(AlreadyExecutedError):
        await service.execute_action(db_session, actor=actor, action=action)


async def test_reverse_action_only_allowed_from_completed(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="loyalty_credit",
        value_minor=None,
        points=100,
        description="100 bonus points.",
    )
    with pytest.raises(InvalidActionStatusTransitionError):
        await service.reverse_action(db_session, actor=actor, action=action, reason="Mistake.")

    executed = await service.execute_action(db_session, actor=actor, action=action)
    reversed_action = await service.reverse_action(
        db_session, actor=actor, action=executed, reason="Issued in error."
    )
    assert reversed_action.status == "reversed"
    assert reversed_action.reversed_by_staff_id == actor.id


async def test_list_action_history_is_chronological(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, actor=actor, customer_id=customer.id)
    action = await service.propose_action(
        db_session,
        actor=actor,
        complaint=complaint,
        recovery_type="apology_only",
        value_minor=None,
        points=None,
        description="Apology.",
    )
    await service.execute_action(db_session, actor=actor, action=action)
    history = await service.list_action_history(db_session, action.id)
    assert [row.to_status for row in history] == ["proposed", "executing", "completed"]


async def test_update_approval_rule_applies_partial_update(db_session: AsyncSession) -> None:
    rule = await service.create_approval_rule(
        db_session,
        payload=ApprovalRuleCreateIn(
            code=f"update-{uuid.uuid4().hex[:8]}",
            name="Updatable rule",
            required_permission="recovery.approve",
        ),
    )
    updated = await service.update_approval_rule(
        db_session, rule=rule, payload=ApprovalRuleUpdateIn(is_active=False)
    )
    assert updated.is_active is False
    assert updated.name == "Updatable rule"
