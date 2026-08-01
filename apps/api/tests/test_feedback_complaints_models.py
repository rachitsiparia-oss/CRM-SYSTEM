"""Model-level constraint tests for Phase 13 (feedback, review requests,
complaints, service recovery) — CHECK constraints, uniqueness, and the
mutual feedback<->complaint FK added via the migration's deferred
`ALTER TABLE`. Service-layer/workflow correctness is covered by
test_feedback_service.py/test_complaints_service.py/
test_service_recovery_service.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.db.models import (
    CompensationApprovalRule,
    Complaint,
    ComplaintLink,
    Customer,
    FeedbackEntry,
    FeedbackRating,
    Order,
    ReviewRequest,
    ServiceRecoveryAction,
    StaffUser,
)
from sqlalchemy.exc import IntegrityError
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


async def _make_order(session: AsyncSession, **overrides: object) -> Order:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "order_number": f"ORD-{suffix}",
        "source": "manual",
        "order_type": "takeaway",
        "status": "draft",
        "payment_status": "pending",
    }
    fields.update(overrides)
    order = Order(**fields)
    session.add(order)
    await session.flush()
    return order


async def _make_complaint(
    session: AsyncSession, customer_id: uuid.UUID, **overrides: object
) -> Complaint:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "complaint_number": f"CMP-{suffix}",
        "customer_id": customer_id,
        "source_type": "direct",
        "category": "delay",
        "title": "Test complaint",
        "description": "Test description",
        "severity": "medium",
        "priority": "normal",
        "status": "new",
    }
    fields.update(overrides)
    complaint = Complaint(**fields)
    session.add(complaint)
    await session.flush()
    return complaint


# --- FeedbackEntry -------------------------------------------------------


async def test_feedback_entry_requires_customer_or_guest_identity(db_session: AsyncSession) -> None:
    entry = FeedbackEntry(
        id=uuid.uuid4(),
        feedback_number=f"FB-{uuid.uuid4().hex[:8]}",
        customer_id=None,
        guest_name=None,
        guest_contact=None,
        source="manual_entry",
    )
    db_session.add(entry)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_feedback_entry_allows_guest_identity_without_customer(
    db_session: AsyncSession,
) -> None:
    entry = FeedbackEntry(
        id=uuid.uuid4(),
        feedback_number=f"FB-{uuid.uuid4().hex[:8]}",
        customer_id=None,
        guest_name="Walk-in Guest",
        source="manual_entry",
    )
    db_session.add(entry)
    await db_session.flush()
    assert entry.status == "new"
    assert entry.priority == "normal"


async def test_feedback_entry_rejects_invalid_source(db_session: AsyncSession) -> None:
    customer = await _make_customer(db_session)
    entry = FeedbackEntry(
        id=uuid.uuid4(),
        feedback_number=f"FB-{uuid.uuid4().hex[:8]}",
        customer_id=customer.id,
        source="carrier_pigeon",
    )
    db_session.add(entry)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_feedback_rating_rejects_out_of_range(db_session: AsyncSession) -> None:
    customer = await _make_customer(db_session)
    entry = FeedbackEntry(
        id=uuid.uuid4(),
        feedback_number=f"FB-{uuid.uuid4().hex[:8]}",
        customer_id=customer.id,
        source="manual_entry",
    )
    db_session.add(entry)
    await db_session.flush()
    db_session.add(FeedbackRating(feedback_id=entry.id, dimension="overall", rating=6))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_feedback_rating_unique_per_dimension(db_session: AsyncSession) -> None:
    customer = await _make_customer(db_session)
    entry = FeedbackEntry(
        id=uuid.uuid4(),
        feedback_number=f"FB-{uuid.uuid4().hex[:8]}",
        customer_id=customer.id,
        source="manual_entry",
    )
    db_session.add(entry)
    await db_session.flush()
    db_session.add(FeedbackRating(feedback_id=entry.id, dimension="overall", rating=4))
    await db_session.flush()
    db_session.add(FeedbackRating(feedback_id=entry.id, dimension="overall", rating=5))
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- ReviewRequest ---------------------------------------------------------


async def test_review_request_rejects_mismatched_source_reference(
    db_session: AsyncSession,
) -> None:
    customer = await _make_customer(db_session)
    review_request = ReviewRequest(
        id=uuid.uuid4(),
        customer_id=customer.id,
        source_type="order",
        order_id=None,
        reservation_id=None,
        channel="whatsapp",
        idempotency_key=f"order:{uuid.uuid4()}",
    )
    db_session.add(review_request)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_review_request_idempotency_key_is_unique(db_session: AsyncSession) -> None:
    customer = await _make_customer(db_session)
    order = await _make_order(db_session)
    key = f"order:{uuid.uuid4()}"
    db_session.add(
        ReviewRequest(
            id=uuid.uuid4(),
            customer_id=customer.id,
            source_type="order",
            order_id=order.id,
            channel="whatsapp",
            idempotency_key=key,
        )
    )
    await db_session.flush()
    db_session.add(
        ReviewRequest(
            id=uuid.uuid4(),
            customer_id=customer.id,
            source_type="order",
            order_id=order.id,
            channel="whatsapp",
            idempotency_key=key,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- Complaint / ComplaintLink ---------------------------------------------


async def test_complaint_defaults_is_hr_sensitive_false(db_session: AsyncSession) -> None:
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, customer.id)
    assert complaint.is_hr_sensitive is False
    assert complaint.current_escalation_level == 0
    assert complaint.reopened_count == 0


async def test_complaint_link_rejects_self_link(db_session: AsyncSession) -> None:
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, customer.id)
    db_session.add(
        ComplaintLink(
            complaint_id=complaint.id,
            related_complaint_id=complaint.id,
            relationship_type="related_to",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_complaint_rejects_invalid_severity(db_session: AsyncSession) -> None:
    customer = await _make_customer(db_session)
    with pytest.raises(IntegrityError):
        await _make_complaint(db_session, customer.id, severity="apocalyptic")


async def test_feedback_converted_to_complaint_fk_resolves(db_session: AsyncSession) -> None:
    """The mutual-reference FK added via the migration's deferred
    `ALTER TABLE` (feedback_entries.converted_to_complaint_id ->
    complaints.id) — a complaint id that doesn't exist must be rejected."""
    customer = await _make_customer(db_session)
    entry = FeedbackEntry(
        id=uuid.uuid4(),
        feedback_number=f"FB-{uuid.uuid4().hex[:8]}",
        customer_id=customer.id,
        source="manual_entry",
        converted_to_complaint_id=uuid.uuid4(),
    )
    db_session.add(entry)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- ServiceRecoveryAction / CompensationApprovalRule -----------------------


async def test_service_recovery_action_rejects_negative_value(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    customer = await _make_customer(db_session)
    complaint = await _make_complaint(db_session, customer.id)
    staff = await make_staff_user()
    action = ServiceRecoveryAction(
        id=uuid.uuid4(),
        complaint_id=complaint.id,
        customer_id=customer.id,
        recovery_type="discount",
        status="proposed",
        value_minor=-500,
        description="Invalid negative discount",
        proposed_by_staff_id=staff.id,
        idempotency_key=f"complaint:{complaint.id}:recovery:{uuid.uuid4()}",
    )
    db_session.add(action)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_compensation_approval_rule_rejects_invalid_value_range(
    db_session: AsyncSession,
) -> None:
    rule = CompensationApprovalRule(
        id=uuid.uuid4(),
        code=f"rule-{uuid.uuid4().hex[:8]}",
        name="Invalid range rule",
        min_value_minor=10_000,
        max_value_minor=1_000,
        required_permission="recovery.approve",
    )
    db_session.add(rule)
    with pytest.raises(IntegrityError):
        await db_session.flush()
