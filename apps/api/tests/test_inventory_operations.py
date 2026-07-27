"""Stock operations — receipts, adjustments, wastage, transfers, and stock
counts (`app.inventory.receipts` / `.adjustments` / `.wastage` /
`.transfers` / `.stock_counts`).
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal

import pytest
from app.db.models import StaffUser
from app.inventory import adjustments as adjustments_service
from app.inventory import ledger
from app.inventory import receipts as receipts_service
from app.inventory import stock_counts as stock_counts_service
from app.inventory import transfers as transfers_service
from app.inventory import wastage as wastage_service
from app.inventory.errors import AlreadyPostedError, NotPostedError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests._inventory_helpers import make_location, make_stack, make_supplier

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]
ZERO = Decimal("0.000")


async def _balance(session: AsyncSession, item_id: uuid.UUID, location_id: uuid.UUID):
    from app.db.models import StockBalance

    return await session.scalar(
        select(StockBalance).where(
            StockBalance.inventory_item_id == item_id,
            StockBalance.storage_location_id == location_id,
            StockBalance.batch_id.is_(None),
        )
    )


# --- Receipts --------------------------------------------------------------


async def test_receipt_post_creates_movement_and_updates_cost(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, location, unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    supplier = await make_supplier(db_session)

    receipt = await receipts_service.create_receipt(
        db_session,
        actor=actor,
        supplier_id=supplier.id,
        storage_location_id=location.id,
        received_date=date.today(),
        supplier_reference=None,
        notes=None,
    )
    await receipts_service.add_receipt_item(
        db_session,
        receipt=receipt,
        inventory_item_id=item.id,
        purchase_unit_id=unit.id,
        received_quantity=Decimal("10"),
        accepted_quantity=Decimal("10"),
        rejected_quantity=ZERO,
        unit_cost_minor=500,
        batch_code=None,
        manufactured_at=None,
        expires_at=None,
        notes=None,
    )
    await receipts_service.post_receipt(db_session, actor=actor, receipt=receipt, request=None)

    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("10.000")
    await db_session.refresh(item)
    assert item.latest_purchase_cost_minor == 500
    assert receipt.status == "posted"
    assert receipt.total_value_minor == 5000


async def test_receipt_with_batch_tracked_item_sets_remaining_quantity_correctly(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    """Regression test for the batch double-counting bug: a freshly
    created batch's `remaining_quantity` must equal exactly the accepted
    quantity, not double it."""
    item, location, unit = await make_stack(db_session, requires_batch_tracking=True)
    actor = await make_staff_user(role_code="owner")
    supplier = await make_supplier(db_session)

    receipt = await receipts_service.create_receipt(
        db_session,
        actor=actor,
        supplier_id=supplier.id,
        storage_location_id=location.id,
        received_date=date.today(),
        supplier_reference=None,
        notes=None,
    )
    await receipts_service.add_receipt_item(
        db_session,
        receipt=receipt,
        inventory_item_id=item.id,
        purchase_unit_id=unit.id,
        received_quantity=Decimal("15"),
        accepted_quantity=Decimal("15"),
        rejected_quantity=ZERO,
        unit_cost_minor=200,
        batch_code="BATCH-A",
        manufactured_at=None,
        expires_at=None,
        notes=None,
    )
    await receipts_service.post_receipt(db_session, actor=actor, receipt=receipt, request=None)

    from app.db.models import InventoryBatch

    batch = await db_session.scalar(
        select(InventoryBatch).where(
            InventoryBatch.inventory_item_id == item.id, InventoryBatch.batch_code == "BATCH-A"
        )
    )
    assert batch is not None
    assert batch.received_quantity == Decimal("15.000")
    assert batch.remaining_quantity == Decimal("15.000")


async def test_receipt_cannot_be_edited_once_posted(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, location, unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    supplier = await make_supplier(db_session)
    receipt = await receipts_service.create_receipt(
        db_session,
        actor=actor,
        supplier_id=supplier.id,
        storage_location_id=location.id,
        received_date=date.today(),
        supplier_reference=None,
        notes=None,
    )
    await receipts_service.add_receipt_item(
        db_session,
        receipt=receipt,
        inventory_item_id=item.id,
        purchase_unit_id=unit.id,
        received_quantity=Decimal("1"),
        accepted_quantity=Decimal("1"),
        rejected_quantity=ZERO,
        unit_cost_minor=100,
        batch_code=None,
        manufactured_at=None,
        expires_at=None,
        notes=None,
    )
    await receipts_service.post_receipt(db_session, actor=actor, receipt=receipt, request=None)

    with pytest.raises(AlreadyPostedError):
        await receipts_service.add_receipt_item(
            db_session,
            receipt=receipt,
            inventory_item_id=item.id,
            purchase_unit_id=unit.id,
            received_quantity=Decimal("1"),
            accepted_quantity=Decimal("1"),
            rejected_quantity=ZERO,
            unit_cost_minor=100,
            batch_code=None,
            manufactured_at=None,
            expires_at=None,
            notes=None,
        )


async def test_receipt_reversal_undoes_stock_effect(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, location, unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    supplier = await make_supplier(db_session)
    receipt = await receipts_service.create_receipt(
        db_session,
        actor=actor,
        supplier_id=supplier.id,
        storage_location_id=location.id,
        received_date=date.today(),
        supplier_reference=None,
        notes=None,
    )
    await receipts_service.add_receipt_item(
        db_session,
        receipt=receipt,
        inventory_item_id=item.id,
        purchase_unit_id=unit.id,
        received_quantity=Decimal("10"),
        accepted_quantity=Decimal("10"),
        rejected_quantity=ZERO,
        unit_cost_minor=100,
        batch_code=None,
        manufactured_at=None,
        expires_at=None,
        notes=None,
    )
    await receipts_service.post_receipt(db_session, actor=actor, receipt=receipt, request=None)
    await receipts_service.reverse_receipt(
        db_session, actor=actor, receipt=receipt, reason="wrong item", request=None
    )

    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == ZERO
    assert receipt.status == "reversed"

    with pytest.raises(NotPostedError):
        await receipts_service.reverse_receipt(
            db_session, actor=actor, receipt=receipt, reason="again", request=None
        )


# --- Adjustments -------------------------------------------------------------


async def test_adjustment_decrease_posts_negative_movement(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, location, _unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=actor.id,
    )

    adjustment = await adjustments_service.create_adjustment(
        db_session,
        actor=actor,
        inventory_item_id=item.id,
        storage_location_id=location.id,
        batch_id=None,
        direction="decrease",
        quantity=Decimal("3"),
        reason_category="damaged",
        reason="test",
        approved_by=actor.id,
        idempotency_key=None,
        request=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("7.000")
    # value_impact_minor is an unsigned magnitude (3 * standard_cost_minor
    # 1000); `direction` carries which way the value moved.
    assert adjustment.value_impact_minor == 3000
    assert adjustment.direction == "decrease"


# --- Wastage -----------------------------------------------------------------


async def test_wastage_always_decreases_stock(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, location, _unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("5"),
        actor_id=actor.id,
    )
    await wastage_service.record_wastage(
        db_session,
        actor=actor,
        inventory_item_id=item.id,
        storage_location_id=location.id,
        batch_id=None,
        quantity=Decimal("5"),
        reason_category="spoilage",
        reason="test",
        station=None,
        related_order_id=None,
        approved_by=None,
        idempotency_key=None,
        request=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == ZERO


# --- Transfers -----------------------------------------------------------


async def test_transfer_creates_both_out_and_in_movements(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, source, _unit = await make_stack(db_session)
    destination = await make_location(db_session)
    actor = await make_staff_user(role_code="owner")
    await ledger.post_movement(
        db_session,
        item=item,
        location=source,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=actor.id,
    )

    transfer = await transfers_service.create_transfer(
        db_session,
        actor=actor,
        source_location_id=source.id,
        destination_location_id=destination.id,
        notes=None,
    )
    await transfers_service.add_transfer_item(
        db_session,
        transfer=transfer,
        inventory_item_id=item.id,
        batch_id=None,
        quantity=Decimal("4"),
        notes=None,
    )
    await transfers_service.post_transfer(db_session, actor=actor, transfer=transfer, request=None)

    source_balance = await _balance(db_session, item.id, source.id)
    dest_balance = await _balance(db_session, item.id, destination.id)
    assert source_balance.on_hand_quantity == Decimal("6.000")
    assert dest_balance.on_hand_quantity == Decimal("4.000")


async def test_transfer_rejects_same_source_and_destination(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    from fastapi import HTTPException

    _item, location, _unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    with pytest.raises(HTTPException):
        await transfers_service.create_transfer(
            db_session,
            actor=actor,
            source_location_id=location.id,
            destination_location_id=location.id,
            notes=None,
        )


async def test_transfer_reversal_undoes_both_legs(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, source, _unit = await make_stack(db_session)
    destination = await make_location(db_session)
    actor = await make_staff_user(role_code="owner")
    await ledger.post_movement(
        db_session,
        item=item,
        location=source,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=actor.id,
    )
    transfer = await transfers_service.create_transfer(
        db_session,
        actor=actor,
        source_location_id=source.id,
        destination_location_id=destination.id,
        notes=None,
    )
    await transfers_service.add_transfer_item(
        db_session,
        transfer=transfer,
        inventory_item_id=item.id,
        batch_id=None,
        quantity=Decimal("4"),
        notes=None,
    )
    await transfers_service.post_transfer(db_session, actor=actor, transfer=transfer, request=None)
    await transfers_service.reverse_transfer(
        db_session, actor=actor, transfer=transfer, reason="wrong destination", request=None
    )

    source_balance = await _balance(db_session, item.id, source.id)
    dest_balance = await _balance(db_session, item.id, destination.id)
    assert source_balance.on_hand_quantity == Decimal("10.000")
    assert dest_balance.on_hand_quantity == ZERO


# --- Stock counts -----------------------------------------------------------


async def test_stock_count_full_lifecycle_generates_correction_for_variance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, location, _unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("20"),
        actor_id=actor.id,
    )

    count = await stock_counts_service.create_count(
        db_session, actor=actor, storage_location_id=location.id, scheduled_date=None, notes=None
    )
    count = await stock_counts_service.start_count(db_session, actor=actor, count=count)

    from app.db.models import StockCountLine

    lines = (
        await db_session.scalars(select(StockCountLine).where(StockCountLine.count_id == count.id))
    ).all()
    assert len(lines) == 1
    line = lines[0]
    assert line.system_quantity == Decimal("20.000")

    await stock_counts_service.record_count_line(
        db_session,
        count=count,
        line=line,
        counted_quantity=Decimal("17"),
        reason="shrinkage",
        notes=None,
    )
    count = await stock_counts_service.submit_count(
        db_session, actor=actor, count=count, request=None
    )
    count = await stock_counts_service.approve_count(
        db_session, actor=actor, count=count, request=None
    )

    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("17.000")
    assert count.status == "approved"


async def test_stock_count_prevents_second_active_session_same_location(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    from app.inventory.errors import InvalidCountStateError

    _item, location, _unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    await stock_counts_service.create_count(
        db_session, actor=actor, storage_location_id=location.id, scheduled_date=None, notes=None
    )
    with pytest.raises(InvalidCountStateError):
        await stock_counts_service.create_count(
            db_session,
            actor=actor,
            storage_location_id=location.id,
            scheduled_date=None,
            notes=None,
        )


async def test_stock_count_submit_requires_every_line_counted(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    from app.inventory.errors import InvalidCountStateError

    item, location, _unit = await make_stack(db_session)
    actor = await make_staff_user(role_code="owner")
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("5"),
        actor_id=actor.id,
    )
    count = await stock_counts_service.create_count(
        db_session, actor=actor, storage_location_id=location.id, scheduled_date=None, notes=None
    )
    count = await stock_counts_service.start_count(db_session, actor=actor, count=count)
    with pytest.raises(InvalidCountStateError):
        await stock_counts_service.submit_count(db_session, actor=actor, count=count, request=None)
