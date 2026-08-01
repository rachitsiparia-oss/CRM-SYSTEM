"""Service-layer workflow tests for feedback and review requests —
`app.feedback.service`/`app.feedback.review_requests`. HTTP-layer
permission enforcement is covered by test_feedback_complaints_api.py;
CHECK-constraint correctness by test_feedback_complaints_models.py.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from app.communications.consent import record_consent
from app.db.models import Customer, Order, Reservation, StaffUser
from app.feedback import review_requests, service
from app.feedback.errors import (
    AlreadyConvertedError,
    DuplicateReviewRequestError,
    InvalidStatusTransitionError,
    TransitionNotPermittedError,
)
from app.feedback.schemas import (
    ConvertToComplaintIn,
    FeedbackCreateIn,
    RatingIn,
    ReviewRequestCompleteIn,
    ReviewRequestCreateIn,
)
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
        "primary_phone_e164": "+919876543210",
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
        "status": "completed",
        "payment_status": "paid",
    }
    fields.update(overrides)
    order = Order(**fields)
    session.add(order)
    await session.flush()
    return order


async def _make_reservation(session: AsyncSession, **overrides: object) -> Reservation:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "reservation_number": f"RES-{suffix}",
        "source": "phone",
        "guest_name": "Test Guest",
        "party_size": 2,
        "reservation_date": datetime.now(UTC).date(),
        "start_time": datetime.now(UTC).time(),
        "status": "completed",
    }
    fields.update(overrides)
    reservation = Reservation(**fields)
    session.add(reservation)
    await session.flush()
    return reservation


# --- Feedback CRUD/transitions ---------------------------------------------


async def test_create_feedback_requires_customer_or_guest(db_session: AsyncSession) -> None:
    with pytest.raises(ValueError):
        FeedbackCreateIn(source="manual_entry")


async def test_create_feedback_stores_ratings(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    feedback = await service.create_feedback(
        db_session,
        actor=actor,
        payload=FeedbackCreateIn(
            customer_id=customer.id,
            source="manual_entry",
            comment="Great meal",
            ratings=[RatingIn(dimension="overall", rating=5)],
        ),
    )
    ratings = await service.list_ratings(db_session, feedback.id)
    assert len(ratings) == 1
    assert ratings[0].rating == 5
    history = await service.list_status_history(db_session, feedback.id)
    assert len(history) == 1
    assert history[0].to_status == "new"


async def test_feedback_transition_follows_state_machine(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    feedback = await service.create_feedback(
        db_session, actor=actor, payload=FeedbackCreateIn(customer_id=customer.id, source="website")
    )
    with pytest.raises(InvalidStatusTransitionError):
        await service.transition_feedback(
            db_session, actor=actor, feedback=feedback, target_status="resolved"
        )
    feedback = await service.transition_feedback(
        db_session, actor=actor, feedback=feedback, target_status="acknowledged"
    )
    assert feedback.acknowledged_at is not None


async def test_feedback_resolve_transition_requires_permission(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    # front_of_house_staff holds feedback.create/update but not
    # feedback.resolve — see app/permissions/role_matrix.py.
    limited_actor = await make_staff_user(role_code="front_of_house_staff")
    customer = await _make_customer(db_session)
    feedback = await service.create_feedback(
        db_session,
        actor=limited_actor,
        payload=FeedbackCreateIn(customer_id=customer.id, source="website"),
    )
    feedback = await service.transition_feedback(
        db_session, actor=limited_actor, feedback=feedback, target_status="acknowledged"
    )
    with pytest.raises(TransitionNotPermittedError):
        await service.transition_feedback(
            db_session, actor=limited_actor, feedback=feedback, target_status="resolved"
        )


async def test_convert_to_complaint_is_explicit_and_not_reentrant(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    feedback = await service.create_feedback(
        db_session,
        actor=actor,
        payload=FeedbackCreateIn(
            customer_id=customer.id, source="whatsapp", comment="Terrible experience"
        ),
    )
    complaint = await service.convert_to_complaint(
        db_session,
        actor=actor,
        feedback=feedback,
        payload=ConvertToComplaintIn(
            category="food_quality", severity="high", title="Bad food quality"
        ),
    )
    assert complaint.feedback_id == feedback.id
    assert feedback.converted_to_complaint_id == complaint.id

    with pytest.raises(AlreadyConvertedError):
        await service.convert_to_complaint(
            db_session,
            actor=actor,
            feedback=feedback,
            payload=ConvertToComplaintIn(
                category="food_quality", severity="high", title="Bad food quality (again)"
            ),
        )


# --- Review requests ---------------------------------------------------------


async def test_review_request_suppressed_without_consent(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)
    review_request = await review_requests.create_review_request(
        db_session,
        actor=actor,
        payload=ReviewRequestCreateIn(
            customer_id=customer.id, source_type="order", order_id=order.id, channel="whatsapp"
        ),
    )
    assert review_request.status == "suppressed"
    assert review_request.suppression_reason == "no_consent"


async def test_review_request_duplicate_is_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)
    payload = ReviewRequestCreateIn(
        customer_id=customer.id, source_type="order", order_id=order.id, channel="whatsapp"
    )
    await review_requests.create_review_request(db_session, actor=actor, payload=payload)
    with pytest.raises(DuplicateReviewRequestError):
        await review_requests.create_review_request(db_session, actor=actor, payload=payload)


async def test_review_request_full_lifecycle_and_low_rating_auto_escalation(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)
    await record_consent(
        db_session,
        customer_id=customer.id,
        consent_type="promotional_whatsapp",
        consent_given=True,
        source="staff_entry",
        actor=actor,
    )

    review_request = await review_requests.create_review_request(
        db_session,
        actor=actor,
        payload=ReviewRequestCreateIn(
            customer_id=customer.id, source_type="order", order_id=order.id, channel="whatsapp"
        ),
    )
    assert review_request.status == "eligible"

    review_request = await review_requests.mark_scheduled(
        db_session, review_request=review_request, scheduled_at=datetime.now(UTC)
    )
    review_request = await review_requests.mark_sent(db_session, review_request=review_request)
    review_request = await review_requests.mark_delivered(db_session, review_request=review_request)
    review_request = await review_requests.mark_opened(db_session, review_request=review_request)

    review_request = await review_requests.complete_review_request(
        db_session,
        actor=actor,
        review_request=review_request,
        payload=ReviewRequestCompleteIn(
            comment="Order was very late.",
            sentiment="negative",
            ratings=[RatingIn(dimension="overall", rating=1)],
        ),
    )
    assert review_request.status == "completed"
    assert review_request.resulting_feedback_id is not None

    feedback = await service.get_feedback(db_session, review_request.resulting_feedback_id)
    assert feedback is not None
    # "Low rating creates action-required status" —
    # INTEGRATIONS_AUTOMATIONS_REALTIME.md section 14.6.
    assert feedback.status == "action_required"


async def test_review_request_cooldown_suppresses_second_request(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order_a = await _make_order(db_session, customer_id=customer.id)
    order_b = await _make_order(db_session, customer_id=customer.id)
    await record_consent(
        db_session,
        customer_id=customer.id,
        consent_type="promotional_whatsapp",
        consent_given=True,
        source="staff_entry",
        actor=actor,
    )

    first = await review_requests.create_review_request(
        db_session,
        actor=actor,
        payload=ReviewRequestCreateIn(
            customer_id=customer.id, source_type="order", order_id=order_a.id, channel="whatsapp"
        ),
    )
    assert first.status == "eligible"

    second = await review_requests.create_review_request(
        db_session,
        actor=actor,
        payload=ReviewRequestCreateIn(
            customer_id=customer.id, source_type="order", order_id=order_b.id, channel="whatsapp"
        ),
    )
    assert second.status == "suppressed"
    assert second.suppression_reason == "cooldown_active"


async def test_process_pending_review_requests_expires_stale_sent(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    order = await _make_order(db_session, customer_id=customer.id)
    await record_consent(
        db_session,
        customer_id=customer.id,
        consent_type="promotional_whatsapp",
        consent_given=True,
        source="staff_entry",
        actor=actor,
    )
    review_request = await review_requests.create_review_request(
        db_session,
        actor=actor,
        payload=ReviewRequestCreateIn(
            customer_id=customer.id, source_type="order", order_id=order.id, channel="whatsapp"
        ),
    )
    review_request = await review_requests.mark_scheduled(
        db_session, review_request=review_request, scheduled_at=datetime.now(UTC)
    )
    review_request = await review_requests.mark_sent(db_session, review_request=review_request)
    review_request.created_at = datetime.now(UTC) - timedelta(days=20)
    await db_session.flush()

    processed = await review_requests.process_pending_review_requests(db_session)
    processed_ids = {row.id for row in processed}
    assert review_request.id in processed_ids
    await db_session.refresh(review_request)
    assert review_request.status == "expired"


async def test_review_request_reservation_source(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await _make_customer(db_session)
    reservation = await _make_reservation(db_session, customer_id=customer.id)
    await record_consent(
        db_session,
        customer_id=customer.id,
        consent_type="promotional_whatsapp",
        consent_given=True,
        source="staff_entry",
        actor=actor,
    )
    review_request = await review_requests.create_review_request(
        db_session,
        actor=actor,
        payload=ReviewRequestCreateIn(
            customer_id=customer.id,
            source_type="reservation",
            reservation_id=reservation.id,
            channel="whatsapp",
        ),
    )
    assert review_request.status == "eligible"
    assert review_request.reservation_id == reservation.id
