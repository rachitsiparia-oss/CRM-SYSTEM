import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.db.models import (
    Customer,
    CustomerAddress,
    CustomerConsent,
    CustomerMergeEvent,
    CustomerNote,
    CustomerTag,
    StaffUser,
    Tag,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _customer_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": "Test Customer",
        "first_name": "Test",
        "last_name": "Customer",
    }
    base.update(overrides)
    return base


async def test_customer_rejects_invalid_customer_type(db_session: AsyncSession) -> None:
    customer = Customer(**_customer_kwargs(customer_type="not_a_real_type"))
    db_session.add(customer)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_rejects_invalid_status(db_session: AsyncSession) -> None:
    customer = Customer(**_customer_kwargs(customer_status="not_a_real_status"))
    db_session.add(customer)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_rejects_invalid_segment(db_session: AsyncSession) -> None:
    customer = Customer(**_customer_kwargs(customer_segment="not_a_real_segment"))
    db_session.add(customer)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_rejects_invalid_dietary_preference(db_session: AsyncSession) -> None:
    customer = Customer(**_customer_kwargs(dietary_preference="not_a_real_preference"))
    db_session.add(customer)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_rejects_invalid_spice_preference(db_session: AsyncSession) -> None:
    customer = Customer(**_customer_kwargs(spice_preference="not_a_real_preference"))
    db_session.add(customer)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_number_is_unique(db_session: AsyncSession) -> None:
    number = f"CUST-{uuid.uuid4().hex[:10]}"
    db_session.add(Customer(**_customer_kwargs(customer_number=number)))
    await db_session.flush()

    db_session.add(Customer(**_customer_kwargs(customer_number=number)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_defaults_stay_honest_until_orders_exist(db_session: AsyncSession) -> None:
    """Regression test for the Phase 5 instruction not to fabricate
    order-derived metrics: a freshly created customer must show zero/NULL
    everywhere those metrics live, never a seeded-looking number."""
    customer = Customer(**_customer_kwargs())
    db_session.add(customer)
    await db_session.flush()

    assert customer.customer_type == "individual"
    assert customer.customer_status == "active"
    assert customer.completed_order_count == 0
    assert customer.lifetime_value_minor == 0
    assert customer.average_order_value_minor == 0
    assert customer.first_order_at is None
    assert customer.last_order_at is None


async def test_customer_address_second_default_conflicts_while_both_active(
    db_session: AsyncSession,
) -> None:
    customer = Customer(**_customer_kwargs())
    db_session.add(customer)
    await db_session.flush()

    db_session.add(
        CustomerAddress(
            id=uuid.uuid4(),
            customer_id=customer.id,
            address_line1="1 First St",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            is_default=True,
        )
    )
    await db_session.flush()

    db_session.add(
        CustomerAddress(
            id=uuid.uuid4(),
            customer_id=customer.id,
            address_line1="2 Second St",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560002",
            is_default=True,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_note_rejects_invalid_note_type(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    customer = Customer(**_customer_kwargs())
    db_session.add(customer)
    staff_user = await make_staff_user()
    await db_session.flush()

    note = CustomerNote(
        id=uuid.uuid4(),
        customer_id=customer.id,
        note_type="not_a_real_type",
        content="Some note.",
        created_by=staff_user.id,
    )
    db_session.add(note)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_consent_unique_per_customer_and_type(db_session: AsyncSession) -> None:
    customer = Customer(**_customer_kwargs())
    db_session.add(customer)
    await db_session.flush()

    db_session.add(
        CustomerConsent(
            id=uuid.uuid4(),
            customer_id=customer.id,
            consent_type="whatsapp_marketing",
            status="granted",
            source="app",
        )
    )
    await db_session.flush()

    db_session.add(
        CustomerConsent(
            id=uuid.uuid4(),
            customer_id=customer.id,
            consent_type="whatsapp_marketing",
            status="withdrawn",
            source="app",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_consent_rejects_invalid_status(db_session: AsyncSession) -> None:
    customer = Customer(**_customer_kwargs())
    db_session.add(customer)
    await db_session.flush()

    db_session.add(
        CustomerConsent(
            id=uuid.uuid4(),
            customer_id=customer.id,
            consent_type="loyalty",
            status="not_a_real_status",
            source="app",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_tag_normalized_name_is_unique(db_session: AsyncSession) -> None:
    normalized = f"vip-{uuid.uuid4().hex[:8]}"
    db_session.add(Tag(id=uuid.uuid4(), name="VIP", normalized_name=normalized))
    await db_session.flush()

    db_session.add(Tag(id=uuid.uuid4(), name="vip", normalized_name=normalized))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_tag_rejects_duplicate_assignment(db_session: AsyncSession) -> None:
    customer = Customer(**_customer_kwargs())
    tag = Tag(id=uuid.uuid4(), name="Regular", normalized_name=f"regular-{uuid.uuid4().hex[:8]}")
    db_session.add_all([customer, tag])
    await db_session.flush()

    db_session.add(CustomerTag(customer_id=customer.id, tag_id=tag.id))
    await db_session.flush()

    db_session.add(CustomerTag(customer_id=customer.id, tag_id=tag.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_merge_event_requires_mapping_summary(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    """`mapping_summary` must be genuinely omitted (SQL NULL), not passed as
    Python `None` — SQLAlchemy's JSONB type serializes an explicit `None`
    to the JSON `null` literal, a valid non-NULL JSONB value that would not
    exercise the NOT NULL constraint."""
    source = Customer(**_customer_kwargs())
    surviving = Customer(**_customer_kwargs())
    db_session.add_all([source, surviving])
    staff_user = await make_staff_user()
    await db_session.flush()

    db_session.add(
        CustomerMergeEvent(
            id=uuid.uuid4(),
            source_customer_id=source.id,
            surviving_customer_id=surviving.id,
            actor_id=staff_user.id,
            reason="Duplicate phone number.",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_customer_assigned_staff_references_real_staff_user(
    db_session: AsyncSession,
) -> None:
    customer = Customer(**_customer_kwargs(assigned_staff_id=uuid.uuid4()))
    db_session.add(customer)
    with pytest.raises(IntegrityError):
        await db_session.flush()
