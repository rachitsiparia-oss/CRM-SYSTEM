"""Commercial-risk flag review queue service tests —
`app.commercial_risk.service`.

Covers `raise_flag`'s default `open` status and `review_flag`'s own
transition map (`_FLAG_TRANSITIONS`): open -> reviewing/resolved/dismissed,
reviewing -> resolved/dismissed, and both terminal states reject any further
transition.
"""

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.commercial_risk import service
from app.commercial_risk.errors import InvalidStatusTransitionError
from app.db.models import Customer, StaffUser
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


async def test_raise_flag_creates_flag_in_open_status(db_session: AsyncSession) -> None:
    flag = await service.raise_flag(
        db_session,
        flag_type="repeated_manual_adjustment",
        summary="Three manual adjustments in one hour.",
    )
    assert flag.status == "open"
    assert flag.reviewed_by is None
    assert flag.reviewed_at is None


async def test_raise_flag_stores_optional_context(db_session: AsyncSession) -> None:
    customer = await _make_customer(db_session)
    related_id = uuid.uuid4()
    flag = await service.raise_flag(
        db_session,
        flag_type="high_value_issuance",
        summary="High-value gift card issued.",
        customer_id=customer.id,
        related_type="gift_card",
        related_id=related_id,
        detail={"amount_minor": 500000},
    )
    assert flag.customer_id == customer.id
    assert flag.related_type == "gift_card"
    assert flag.related_id == related_id
    assert flag.detail == {"amount_minor": 500000}


@pytest.mark.parametrize(
    ("start_status", "target_status"),
    [
        ("open", "reviewing"),
        ("open", "resolved"),
        ("open", "dismissed"),
        ("reviewing", "resolved"),
        ("reviewing", "dismissed"),
    ],
)
async def test_review_flag_allows_documented_transitions(
    db_session: AsyncSession,
    make_staff_user: MakeStaffUser,
    start_status: str,
    target_status: str,
) -> None:
    actor = await make_staff_user(role_code="owner")
    flag = await service.raise_flag(
        db_session, flag_type="duplicate_attempt", summary="Duplicate idempotency key."
    )
    if start_status != "open":
        flag = await service.review_flag(
            db_session,
            actor=actor,
            flag=flag,
            target_status=start_status,  # type: ignore[arg-type]
            resolution_note=None,
        )

    flag = await service.review_flag(
        db_session,
        actor=actor,
        flag=flag,
        target_status=target_status,  # type: ignore[arg-type]
        resolution_note="Reviewed.",
    )
    assert flag.status == target_status
    assert flag.reviewed_by == actor.id
    assert flag.reviewed_at is not None


@pytest.mark.parametrize(
    ("start_status", "target_status"),
    [
        ("open", "open"),
        ("resolved", "reviewing"),
        ("resolved", "dismissed"),
        ("dismissed", "reviewing"),
        ("dismissed", "resolved"),
    ],
)
async def test_review_flag_rejects_undocumented_transitions(
    db_session: AsyncSession,
    make_staff_user: MakeStaffUser,
    start_status: str,
    target_status: str,
) -> None:
    actor = await make_staff_user(role_code="owner")
    flag = await service.raise_flag(
        db_session, flag_type="identity_overlap", summary="Overlapping identity."
    )
    if start_status != "open":
        flag = await service.review_flag(
            db_session,
            actor=actor,
            flag=flag,
            target_status=start_status,  # type: ignore[arg-type]
            resolution_note=None,
        )

    with pytest.raises(InvalidStatusTransitionError):
        await service.review_flag(
            db_session,
            actor=actor,
            flag=flag,
            target_status=target_status,  # type: ignore[arg-type]
            resolution_note=None,
        )


async def test_review_flag_resolution_note_is_optional(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    flag = await service.raise_flag(
        db_session, flag_type="excessive_coupon_failures", summary="5 failed coupon attempts."
    )
    flag = await service.review_flag(
        db_session, actor=actor, flag=flag, target_status="dismissed", resolution_note=None
    )
    assert flag.status == "dismissed"
    assert flag.resolution_note is None
