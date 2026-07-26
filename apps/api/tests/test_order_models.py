import uuid

import pytest
from app.db.models import (
    Order,
    OrderCharge,
    OrderDiscount,
    OrderItem,
    OrderItemModifier,
    OrderPayment,
    OrderSourceMetadata,
    OrderTax,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _order_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "order_number": f"ORD-{suffix}",
        "source": "manual",
        "order_type": "takeaway",
        "status": "draft",
        "payment_status": "pending",
    }
    base.update(overrides)
    return base


async def _make_order(session: AsyncSession, **overrides: object) -> Order:
    order = Order(**_order_kwargs(**overrides))
    session.add(order)
    await session.flush()
    return order


def _item_kwargs(order_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "order_id": order_id,
        "product_name_snapshot": "Test Product",
        "quantity": 1,
        "unit_price_minor": 10000,
        "final_price_minor": 10000,
        "status": "active",
    }
    base.update(overrides)
    return base


# --- Order ------------------------------------------------------------------


async def test_order_rejects_invalid_source(db_session: AsyncSession) -> None:
    db_session.add(Order(**_order_kwargs(source="carrier_pigeon")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_rejects_invalid_order_type(db_session: AsyncSession) -> None:
    db_session.add(Order(**_order_kwargs(order_type="teleport")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_rejects_invalid_status(db_session: AsyncSession) -> None:
    db_session.add(Order(**_order_kwargs(status="floating_around")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_rejects_invalid_payment_status(db_session: AsyncSession) -> None:
    db_session.add(Order(**_order_kwargs(payment_status="unknown")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_rejects_negative_grand_total(db_session: AsyncSession) -> None:
    db_session.add(Order(**_order_kwargs(grand_total_minor=-100)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_number_is_unique(db_session: AsyncSession) -> None:
    number = f"ORD-{uuid.uuid4().hex[:10]}"
    db_session.add(Order(**_order_kwargs(order_number=number)))
    await db_session.flush()

    db_session.add(Order(**_order_kwargs(order_number=number)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_idempotency_key_is_unique_when_set(db_session: AsyncSession) -> None:
    key = f"idem-{uuid.uuid4().hex[:10]}"
    db_session.add(Order(**_order_kwargs(idempotency_key=key)))
    await db_session.flush()

    db_session.add(Order(**_order_kwargs(idempotency_key=key)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_allows_multiple_null_idempotency_keys(db_session: AsyncSession) -> None:
    db_session.add(Order(**_order_kwargs()))
    db_session.add(Order(**_order_kwargs()))
    await db_session.flush()


async def test_order_defaults_to_draft_status(db_session: AsyncSession) -> None:
    kwargs = _order_kwargs()
    del kwargs["status"]
    order = Order(**kwargs)
    db_session.add(order)
    await db_session.flush()
    assert order.status == "draft"


# --- OrderItem ----------------------------------------------------------------


async def test_order_item_rejects_zero_quantity(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(OrderItem(**_item_kwargs(order.id, quantity=0)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_item_rejects_negative_unit_price(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(OrderItem(**_item_kwargs(order.id, unit_price_minor=-1)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_item_rejects_invalid_status(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(OrderItem(**_item_kwargs(order.id, status="in_the_oven")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_item_persists_snapshots(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    item = OrderItem(
        **_item_kwargs(
            order.id,
            product_name_snapshot="RKPR Classic Veg Burger",
            variant_name_snapshot="11-inch",
            product_code_snapshot="PROD-ABC123",
        )
    )
    db_session.add(item)
    await db_session.flush()
    assert item.product_name_snapshot == "RKPR Classic Veg Burger"
    assert item.variant_name_snapshot == "11-inch"


# --- OrderItemModifier --------------------------------------------------------


async def test_order_item_modifier_rejects_zero_quantity(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    item = OrderItem(**_item_kwargs(order.id))
    db_session.add(item)
    await db_session.flush()

    db_session.add(
        OrderItemModifier(
            id=uuid.uuid4(),
            order_item_id=item.id,
            modifier_name_snapshot="Cheese slice",
            price_minor_snapshot=3500,
            quantity=0,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- OrderDiscount ------------------------------------------------------------


async def test_order_discount_rejects_invalid_type(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(
        OrderDiscount(
            id=uuid.uuid4(),
            order_id=order.id,
            discount_type="loyalty_points",
            amount_minor=100,
            reason="test",
            approved_by=uuid.uuid4(),
            created_by=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_discount_rejects_out_of_range_percentage(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(
        OrderDiscount(
            id=uuid.uuid4(),
            order_id=order.id,
            discount_type="percentage",
            amount_minor=100,
            percentage=150,
            reason="test",
            approved_by=uuid.uuid4(),
            created_by=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- OrderTax / OrderCharge ---------------------------------------------------


async def test_order_tax_rejects_negative_amount(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(OrderTax(id=uuid.uuid4(), order_id=order.id, tax_name="GST", amount_minor=-1))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_charge_rejects_invalid_type(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(
        OrderCharge(
            id=uuid.uuid4(), order_id=order.id, charge_type="cover_charge", amount_minor=100
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- OrderPayment --------------------------------------------------------------


async def test_order_payment_rejects_invalid_method(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(
        OrderPayment(
            id=uuid.uuid4(),
            order_id=order.id,
            method="cheque",
            status="paid",
            amount_minor=100,
            recorded_by=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_payment_rejects_negative_amount(db_session: AsyncSession) -> None:
    order = await _make_order(db_session)
    db_session.add(
        OrderPayment(
            id=uuid.uuid4(),
            order_id=order.id,
            method="cash",
            status="paid",
            amount_minor=-1,
            recorded_by=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- OrderSourceMetadata -------------------------------------------------------


async def test_order_source_metadata_external_order_id_unique_when_set(
    db_session: AsyncSession,
) -> None:
    order_a = await _make_order(db_session)
    order_b = await _make_order(db_session)
    external_id = f"ext-{uuid.uuid4().hex[:10]}"

    db_session.add(OrderSourceMetadata(order_id=order_a.id, external_order_id=external_id))
    await db_session.flush()

    db_session.add(OrderSourceMetadata(order_id=order_b.id, external_order_id=external_id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_order_source_metadata_allows_multiple_null_external_ids(
    db_session: AsyncSession,
) -> None:
    order_a = await _make_order(db_session)
    order_b = await _make_order(db_session)
    db_session.add(OrderSourceMetadata(order_id=order_a.id))
    db_session.add(OrderSourceMetadata(order_id=order_b.id))
    await db_session.flush()
