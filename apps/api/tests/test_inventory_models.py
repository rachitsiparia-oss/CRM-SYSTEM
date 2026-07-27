"""Database-constraint tests for the Phase 8 inventory schema — CHECK
constraints, unique constraints, and the append-only trigger on
`stock_movements`. Service-level behavior (ledger, receipts, recipes, ...)
is covered in the other `test_inventory_*.py` files.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.db.models import (
    StockBalance,
    StockCount,
    StockMovement,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests._inventory_helpers import (
    make_batch,
    make_item,
    make_location,
    make_stack,
    make_supplier,
    make_unit,
)

pytestmark = pytest.mark.asyncio

ZERO = Decimal("0.000")


# --- UnitOfMeasure ------------------------------------------------------


async def test_unit_rejects_invalid_unit_type(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await make_unit(db_session, unit_type="temperature")


async def test_unit_rejects_non_positive_conversion_factor(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await make_unit(db_session, conversion_factor=Decimal("0"))


async def test_unit_base_unit_must_have_factor_one(db_session: AsyncSession) -> None:
    # base_unit_id IS NULL requires conversion_factor = 1.
    with pytest.raises(IntegrityError):
        await make_unit(db_session, base_unit_id=None, conversion_factor=Decimal("2"))


async def test_unit_code_is_unique(db_session: AsyncSession) -> None:
    code = f"dup-{uuid.uuid4().hex[:10]}"
    await make_unit(db_session, code=code)
    with pytest.raises(IntegrityError):
        await make_unit(db_session, code=code)


# --- StorageLocation ------------------------------------------------------


async def test_location_rejects_invalid_location_type(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await make_location(db_session, location_type="orbit")


async def test_location_defaults_allows_negative_stock_false(db_session: AsyncSession) -> None:
    location = await make_location(db_session)
    assert location.allows_negative_stock is False


# --- Supplier ------------------------------------------------------------


async def test_supplier_rejects_invalid_status(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        await make_supplier(db_session, status="on_vacation")


async def test_supplier_code_is_unique(db_session: AsyncSession) -> None:
    code = f"SUP-{uuid.uuid4().hex[:10]}"
    await make_supplier(db_session, supplier_code=code)
    with pytest.raises(IntegrityError):
        await make_supplier(db_session, supplier_code=code)


# --- InventoryItem ---------------------------------------------------------


async def test_item_rejects_invalid_stock_status(db_session: AsyncSession) -> None:
    unit = await make_unit(db_session)
    with pytest.raises(IntegrityError):
        await make_item(db_session, base_unit_id=unit.id, stock_status="on_fire")


async def test_item_rejects_negative_reorder_level(db_session: AsyncSession) -> None:
    unit = await make_unit(db_session)
    with pytest.raises(IntegrityError):
        await make_item(db_session, base_unit_id=unit.id, reorder_level=Decimal("-1"))


async def test_item_expiry_tracking_requires_batch_tracking(db_session: AsyncSession) -> None:
    unit = await make_unit(db_session)
    with pytest.raises(IntegrityError):
        await make_item(
            db_session,
            base_unit_id=unit.id,
            requires_batch_tracking=False,
            requires_expiry_tracking=True,
        )


async def test_item_allows_batch_and_expiry_tracking_together(db_session: AsyncSession) -> None:
    unit = await make_unit(db_session)
    item = await make_item(
        db_session,
        base_unit_id=unit.id,
        requires_batch_tracking=True,
        requires_expiry_tracking=True,
    )
    assert item.requires_expiry_tracking is True


async def test_item_code_is_unique(db_session: AsyncSession) -> None:
    unit = await make_unit(db_session)
    code = f"ITM-{uuid.uuid4().hex[:10]}"
    await make_item(db_session, base_unit_id=unit.id, item_code=code)
    with pytest.raises(IntegrityError):
        await make_item(db_session, base_unit_id=unit.id, item_code=code)


async def test_item_barcode_unique_only_when_set(db_session: AsyncSession) -> None:
    unit = await make_unit(db_session)
    barcode = f"barcode-{uuid.uuid4().hex[:10]}"
    await make_item(db_session, base_unit_id=unit.id, barcode=barcode)
    with pytest.raises(IntegrityError):
        await make_item(db_session, base_unit_id=unit.id, barcode=barcode)


async def test_item_allows_multiple_null_barcodes(db_session: AsyncSession) -> None:
    unit = await make_unit(db_session)
    await make_item(db_session, base_unit_id=unit.id)
    await make_item(db_session, base_unit_id=unit.id)


# --- InventoryBatch ---------------------------------------------------------


async def test_batch_rejects_remaining_above_received(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    with pytest.raises(IntegrityError):
        await make_batch(
            db_session,
            item=item,
            location=location,
            received_quantity=Decimal("10"),
            remaining_quantity=Decimal("11"),
        )


async def test_batch_rejects_expiry_before_received_date(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
    with pytest.raises(IntegrityError):
        await make_batch(
            db_session,
            item=item,
            location=location,
            received_quantity=Decimal("10"),
            expires_at=yesterday,
        )


async def test_batch_rejects_expiry_before_manufactured_date(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    today = datetime.now(UTC).date()
    with pytest.raises(IntegrityError):
        await make_batch(
            db_session,
            item=item,
            location=location,
            received_quantity=Decimal("10"),
            manufactured_at=today + timedelta(days=5),
            expires_at=today + timedelta(days=2),
        )


async def test_batch_code_unique_per_item(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    await make_batch(
        db_session, item=item, location=location, received_quantity=Decimal("5"), batch_code="B1"
    )
    with pytest.raises(IntegrityError):
        await make_batch(
            db_session,
            item=item,
            location=location,
            received_quantity=Decimal("5"),
            batch_code="B1",
        )


# --- StockBalance -----------------------------------------------------------


async def test_balance_unique_per_item_location_without_batch(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    db_session.add(
        StockBalance(
            id=uuid.uuid4(),
            inventory_item_id=item.id,
            storage_location_id=location.id,
            batch_id=None,
            on_hand_quantity=ZERO,
            reserved_quantity=ZERO,
        )
    )
    await db_session.flush()
    db_session.add(
        StockBalance(
            id=uuid.uuid4(),
            inventory_item_id=item.id,
            storage_location_id=location.id,
            batch_id=None,
            on_hand_quantity=ZERO,
            reserved_quantity=ZERO,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- StockMovement: sign convention and append-only trigger ----------------


async def test_movement_rejects_zero_quantity_delta(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    db_session.add(
        StockMovement(
            id=uuid.uuid4(),
            movement_number=f"MOV-{uuid.uuid4().hex[:10]}",
            inventory_item_id=item.id,
            storage_location_id=location.id,
            movement_type="opening_balance",
            quantity_delta=ZERO,
            affects_on_hand=True,
            occurred_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_movement_reservation_type_must_not_affect_on_hand(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    db_session.add(
        StockMovement(
            id=uuid.uuid4(),
            movement_number=f"MOV-{uuid.uuid4().hex[:10]}",
            inventory_item_id=item.id,
            storage_location_id=location.id,
            movement_type="order_reservation",
            quantity_delta=Decimal("1.000"),
            affects_on_hand=True,  # wrong — reservations never touch on-hand
            occurred_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_movement_on_hand_type_must_affect_on_hand(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    db_session.add(
        StockMovement(
            id=uuid.uuid4(),
            movement_number=f"MOV-{uuid.uuid4().hex[:10]}",
            inventory_item_id=item.id,
            storage_location_id=location.id,
            movement_type="opening_balance",
            quantity_delta=Decimal("1.000"),
            affects_on_hand=False,  # wrong — opening_balance always affects on-hand
            occurred_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_movement_idempotency_key_unique_when_set(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    key = f"idem-{uuid.uuid4().hex[:10]}"

    def _movement(**overrides: object) -> StockMovement:
        fields: dict[str, object] = {
            "id": uuid.uuid4(),
            "movement_number": f"MOV-{uuid.uuid4().hex[:10]}",
            "inventory_item_id": item.id,
            "storage_location_id": location.id,
            "movement_type": "opening_balance",
            "quantity_delta": Decimal("1.000"),
            "affects_on_hand": True,
            "occurred_at": datetime.now(UTC),
            "idempotency_key": key,
        }
        fields.update(overrides)
        return StockMovement(**fields)

    db_session.add(_movement())
    await db_session.flush()
    db_session.add(_movement())
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_stock_movements_are_append_only_no_delete(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    movement = StockMovement(
        id=uuid.uuid4(),
        movement_number=f"MOV-{uuid.uuid4().hex[:10]}",
        inventory_item_id=item.id,
        storage_location_id=location.id,
        movement_type="opening_balance",
        quantity_delta=Decimal("1.000"),
        affects_on_hand=True,
        occurred_at=datetime.now(UTC),
    )
    db_session.add(movement)
    await db_session.flush()

    with pytest.raises(Exception, match="append-only"):
        await db_session.execute(
            text("DELETE FROM stock_movements WHERE id = :id"), {"id": movement.id}
        )


async def test_stock_movements_are_append_only_no_field_update(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    movement = StockMovement(
        id=uuid.uuid4(),
        movement_number=f"MOV-{uuid.uuid4().hex[:10]}",
        inventory_item_id=item.id,
        storage_location_id=location.id,
        movement_type="opening_balance",
        quantity_delta=Decimal("1.000"),
        affects_on_hand=True,
        occurred_at=datetime.now(UTC),
    )
    db_session.add(movement)
    await db_session.flush()

    with pytest.raises(Exception, match="append-only"):
        await db_session.execute(
            text("UPDATE stock_movements SET reason = 'edited' WHERE id = :id"),
            {"id": movement.id},
        )


async def test_stock_movements_allow_reversal_bookkeeping_update(
    db_session: AsyncSession,
) -> None:
    item, location, _unit = await make_stack(db_session)
    original = StockMovement(
        id=uuid.uuid4(),
        movement_number=f"MOV-{uuid.uuid4().hex[:10]}",
        inventory_item_id=item.id,
        storage_location_id=location.id,
        movement_type="opening_balance",
        quantity_delta=Decimal("1.000"),
        affects_on_hand=True,
        occurred_at=datetime.now(UTC),
    )
    reversal = StockMovement(
        id=uuid.uuid4(),
        movement_number=f"MOV-{uuid.uuid4().hex[:10]}",
        inventory_item_id=item.id,
        storage_location_id=location.id,
        movement_type="reversal",
        quantity_delta=Decimal("-1.000"),
        affects_on_hand=True,
        occurred_at=datetime.now(UTC),
        source_movement_id=original.id,
    )
    db_session.add_all([original, reversal])
    await db_session.flush()

    # Only reversed_by_movement_id/reversed_at may change on a posted row —
    # this is the one exception the trigger allows.
    await db_session.execute(
        text(
            "UPDATE stock_movements SET reversed_by_movement_id = :rid, "
            "reversed_at = now() WHERE id = :id"
        ),
        {"rid": reversal.id, "id": original.id},
    )


# --- StockCount --------------------------------------------------------------


async def test_stock_count_rejects_invalid_status(db_session: AsyncSession) -> None:
    _item, location, _unit = await make_stack(db_session)
    with pytest.raises(IntegrityError):
        db_session.add(
            StockCount(
                id=uuid.uuid4(),
                count_number=f"CNT-{uuid.uuid4().hex[:10]}",
                storage_location_id=location.id,
                status="mid_air",
            )
        )
        await db_session.flush()


async def test_stock_count_prevents_duplicate_active_session_per_location(
    db_session: AsyncSession,
) -> None:
    _item, location, _unit = await make_stack(db_session)
    db_session.add(
        StockCount(
            id=uuid.uuid4(),
            count_number=f"CNT-{uuid.uuid4().hex[:10]}",
            storage_location_id=location.id,
            status="draft",
        )
    )
    await db_session.flush()

    db_session.add(
        StockCount(
            id=uuid.uuid4(),
            count_number=f"CNT-{uuid.uuid4().hex[:10]}",
            storage_location_id=location.id,
            status="in_progress",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
