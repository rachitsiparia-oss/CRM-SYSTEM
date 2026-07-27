"""Goods receipt: draft -> posted -> optionally reversed.

CORE_CRM_MODULES.md section 8.8's documented workflow, and this phase's own
instruction: "Posting a receipt must: validate all lines, convert quantities
to base units, create stock movements, update balances, update latest
purchase cost where appropriate, create audit events, create outbox events
where documented. Posted receipts must become read-only. Correction must
happen through reversal."
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    InventoryBatch,
    InventoryItem,
    StaffUser,
    StockReceipt,
    StockReceiptItem,
    StorageLocation,
    Supplier,
    UnitOfMeasure,
)
from app.inventory import ledger
from app.inventory.errors import AlreadyPostedError, BatchRequiredError, NotPostedError
from app.inventory.units import convert_purchase_quantity, quantize_quantity
from app.outbox.service import record_domain_event

ZERO = Decimal("0.000")


def generate_receipt_number() -> str:
    return f"RCP-{uuid.uuid4().hex[:8].upper()}"


async def create_receipt(
    session: AsyncSession,
    *,
    actor: StaffUser,
    supplier_id: uuid.UUID,
    storage_location_id: uuid.UUID,
    received_date: date,
    supplier_reference: str | None,
    notes: str | None,
) -> StockReceipt:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    location = await session.get(StorageLocation, storage_location_id)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Storage location not found."
        )

    receipt = StockReceipt(
        id=uuid.uuid4(),
        receipt_number=generate_receipt_number(),
        supplier_id=supplier_id,
        storage_location_id=storage_location_id,
        received_date=received_date,
        supplier_reference=supplier_reference,
        notes=notes,
        status="draft",
        created_by=actor.id,
    )
    session.add(receipt)
    await session.flush()
    return receipt


def _assert_draft(receipt: StockReceipt) -> None:
    if receipt.status != "draft":
        raise AlreadyPostedError(
            f"Receipt {receipt.receipt_number} is {receipt.status}; only a draft receipt "
            "can be edited."
        )


async def add_receipt_item(
    session: AsyncSession,
    *,
    receipt: StockReceipt,
    inventory_item_id: uuid.UUID,
    purchase_unit_id: uuid.UUID,
    received_quantity: Decimal,
    accepted_quantity: Decimal,
    rejected_quantity: Decimal,
    unit_cost_minor: int,
    batch_code: str | None,
    manufactured_at: date | None,
    expires_at: date | None,
    notes: str | None,
) -> StockReceiptItem:
    _assert_draft(receipt)

    item = await session.get(InventoryItem, inventory_item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found."
        )
    purchase_unit = await session.get(UnitOfMeasure, purchase_unit_id)
    if purchase_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")
    base_unit = await session.get(UnitOfMeasure, item.base_unit_id)
    assert base_unit is not None

    if item.requires_batch_tracking and not batch_code:
        raise BatchRequiredError(f"{item.name} requires a batch code for every receipt.")

    base_quantity = convert_purchase_quantity(
        accepted_quantity,
        purchase_unit=purchase_unit,
        base_unit=base_unit,
        purchase_conversion_factor=item.purchase_conversion_factor,
    )
    line_total_minor = int((accepted_quantity * Decimal(unit_cost_minor)).to_integral_value())

    receipt_item = StockReceiptItem(
        id=uuid.uuid4(),
        receipt_id=receipt.id,
        inventory_item_id=inventory_item_id,
        purchase_unit_id=purchase_unit_id,
        received_quantity=quantize_quantity(received_quantity),
        accepted_quantity=quantize_quantity(accepted_quantity),
        rejected_quantity=quantize_quantity(rejected_quantity),
        base_quantity=base_quantity,
        unit_cost_minor=unit_cost_minor,
        line_total_minor=line_total_minor,
        batch_code=batch_code,
        manufactured_at=manufactured_at,
        expires_at=expires_at,
        notes=notes,
    )
    session.add(receipt_item)
    await session.flush()
    return receipt_item


async def post_receipt(
    session: AsyncSession, *, actor: StaffUser, receipt: StockReceipt, request: Request | None
) -> StockReceipt:
    _assert_draft(receipt)

    items = (
        await session.scalars(
            select(StockReceiptItem).where(StockReceiptItem.receipt_id == receipt.id)
        )
    ).all()
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A receipt needs at least one line."
        )

    location = await session.get(StorageLocation, receipt.storage_location_id)
    assert location is not None
    now = datetime.now(UTC)
    total_value_minor = 0

    for line in items:
        if line.accepted_quantity <= ZERO:
            continue  # A fully-rejected line creates no stock effect.

        item = await session.get(InventoryItem, line.inventory_item_id)
        assert item is not None

        batch: InventoryBatch | None = None
        if item.requires_batch_tracking:
            assert line.batch_code is not None
            batch = InventoryBatch(
                id=uuid.uuid4(),
                inventory_item_id=item.id,
                batch_code=line.batch_code,
                storage_location_id=receipt.storage_location_id,
                supplier_id=receipt.supplier_id,
                received_quantity=line.base_quantity,
                # Starts at zero, not `line.base_quantity`: the immediately
                # following `ledger.post_movement` call is the batch's
                # sole writer for `remaining_quantity` (it adds the posted
                # movement's signed quantity on top of whatever is already
                # there), exactly like a freshly-created `StockBalance` row.
                # Pre-filling it here would double-count the receipt.
                remaining_quantity=ZERO,
                received_at=now,
                manufactured_at=line.manufactured_at,
                expires_at=line.expires_at,
                unit_cost_minor=line.unit_cost_minor,
                status="active",
                created_by=actor.id,
            )
            session.add(batch)
            await session.flush()
            line.batch_id = batch.id

        # Per-base-unit cost, for the ledger and the item's latest-cost
        # field — the receipt line's unit_cost_minor is per *purchase* unit.
        # line_total_minor / base_quantity is the exact per-base-unit rate;
        # rounded the same way every other quantity/cost figure is
        # (ROUND_HALF_UP), via quantize_quantity's half-up convention.
        if line.base_quantity > ZERO:
            per_base_unit_cost_minor = int(
                (Decimal(line.line_total_minor) / line.base_quantity).to_integral_value(
                    rounding="ROUND_HALF_UP"
                )
            )
        else:
            per_base_unit_cost_minor = line.unit_cost_minor

        await ledger.post_movement(
            session,
            item=item,
            location=location,
            movement_type="purchase_receipt",
            quantity=line.base_quantity,
            batch=batch,
            actor_id=actor.id,
            occurred_at=now,
            reason=f"Goods receipt {receipt.receipt_number}",
            reference_type="stock_receipt_item",
            reference_id=line.id,
            unit_cost_minor=per_base_unit_cost_minor,
            entered_unit_id=line.purchase_unit_id,
            entered_quantity=line.accepted_quantity,
        )

        item.latest_purchase_cost_minor = per_base_unit_cost_minor
        item.last_received_at = now
        if item.standard_cost_minor is None:
            item.standard_cost_minor = per_base_unit_cost_minor
        total_value_minor += line.line_total_minor

    receipt.status = "posted"
    receipt.total_value_minor = total_value_minor
    receipt.posted_by = actor.id
    receipt.posted_at = now
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.receipt.posted",
        target_type="stock_receipt",
        target_id=receipt.id,
        request=request,
        safe_metadata={
            "receipt_number": receipt.receipt_number,
            "total_value_minor": total_value_minor,
            "line_count": len(items),
        },
    )
    await record_domain_event(
        session,
        event_type="inventory.receipt.posted",
        aggregate_type="stock_receipt",
        aggregate_id=receipt.id,
        payload={"receipt_id": str(receipt.id), "receipt_number": receipt.receipt_number},
    )
    return receipt


async def reverse_receipt(
    session: AsyncSession,
    *,
    actor: StaffUser,
    receipt: StockReceipt,
    reason: str,
    request: Request | None,
) -> StockReceipt:
    if receipt.status != "posted":
        raise NotPostedError(f"Receipt {receipt.receipt_number} is not posted; nothing to reverse.")

    from app.db.models import StockMovement

    location = await session.get(StorageLocation, receipt.storage_location_id)
    assert location is not None
    items = (
        await session.scalars(
            select(StockReceiptItem).where(StockReceiptItem.receipt_id == receipt.id)
        )
    ).all()

    for line in items:
        if line.accepted_quantity <= ZERO:
            continue
        original = await session.scalar(
            select(StockMovement).where(
                StockMovement.reference_type == "stock_receipt_item",
                StockMovement.reference_id == line.id,
            )
        )
        if original is None:
            continue
        item = await session.get(InventoryItem, line.inventory_item_id)
        assert item is not None
        batch = await session.get(InventoryBatch, line.batch_id) if line.batch_id else None
        await ledger.reverse_movement(
            session,
            original=original,
            item=item,
            location=location,
            actor_id=actor.id,
            reason=f"Reversal of {receipt.receipt_number}: {reason}",
            batch=batch,
        )

    receipt.status = "reversed"
    receipt.reversed_by = actor.id
    receipt.reversed_at = datetime.now(UTC)
    receipt.reversal_reason = reason
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.receipt.reversed",
        target_type="stock_receipt",
        target_id=receipt.id,
        request=request,
        safe_metadata={"receipt_number": receipt.receipt_number, "reason": reason},
    )
    return receipt
