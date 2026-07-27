"""Internal stock transfers between two storage locations.

This phase's own instruction: "Never create only one side of a transfer,"
"Source and destination locations cannot be the same." Posting always
creates a `transfer_out`/`transfer_in` pair in one transaction.

A batch-tracked item's line must name the specific `batch_id` being moved
(the same "one line, one explicit decision" shape receipts use for batch
codes) rather than auto-splitting across several source batches — a
transfer of a single item across multiple batches is simply multiple lines.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    InventoryBatch,
    InventoryItem,
    StaffUser,
    StockTransfer,
    StockTransferItem,
    StorageLocation,
)
from app.inventory import ledger
from app.inventory.errors import AlreadyPostedError, BatchRequiredError, NotPostedError
from app.inventory.units import quantize_quantity
from app.outbox.service import record_domain_event

ZERO = Decimal("0.000")


def generate_transfer_number() -> str:
    return f"TRF-{uuid.uuid4().hex[:8].upper()}"


async def create_transfer(
    session: AsyncSession,
    *,
    actor: StaffUser,
    source_location_id: uuid.UUID,
    destination_location_id: uuid.UUID,
    notes: str | None,
) -> StockTransfer:
    if source_location_id == destination_location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination locations cannot be the same.",
        )
    source = await session.get(StorageLocation, source_location_id)
    destination = await session.get(StorageLocation, destination_location_id)
    if source is None or destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

    transfer = StockTransfer(
        id=uuid.uuid4(),
        transfer_number=generate_transfer_number(),
        source_location_id=source_location_id,
        destination_location_id=destination_location_id,
        status="draft",
        notes=notes,
        requested_by=actor.id,
        created_by=actor.id,
    )
    session.add(transfer)
    await session.flush()
    return transfer


def _assert_draft(transfer: StockTransfer) -> None:
    if transfer.status != "draft":
        raise AlreadyPostedError(
            f"Transfer {transfer.transfer_number} is {transfer.status}; only a draft "
            "transfer can be edited."
        )


async def add_transfer_item(
    session: AsyncSession,
    *,
    transfer: StockTransfer,
    inventory_item_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    quantity: Decimal,
    notes: str | None,
) -> StockTransferItem:
    _assert_draft(transfer)

    item = await session.get(InventoryItem, inventory_item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found."
        )
    if item.requires_batch_tracking and batch_id is None:
        raise BatchRequiredError(f"{item.name} is batch-tracked: select which batch to transfer.")
    if batch_id is not None:
        batch = await session.get(InventoryBatch, batch_id)
        if batch is None or batch.storage_location_id != transfer.source_location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch not found at the source location.",
            )

    transfer_item = StockTransferItem(
        id=uuid.uuid4(),
        transfer_id=transfer.id,
        inventory_item_id=inventory_item_id,
        batch_id=batch_id,
        quantity=quantize_quantity(quantity),
        notes=notes,
    )
    session.add(transfer_item)
    await session.flush()
    return transfer_item


async def post_transfer(
    session: AsyncSession, *, actor: StaffUser, transfer: StockTransfer, request: Request | None
) -> StockTransfer:
    _assert_draft(transfer)

    items = (
        await session.scalars(
            select(StockTransferItem).where(StockTransferItem.transfer_id == transfer.id)
        )
    ).all()
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A transfer needs at least one line."
        )

    source = await session.get(StorageLocation, transfer.source_location_id)
    destination = await session.get(StorageLocation, transfer.destination_location_id)
    assert source is not None and destination is not None
    now = datetime.now(UTC)

    for line in items:
        item = await session.get(InventoryItem, line.inventory_item_id)
        assert item is not None

        source_batch: InventoryBatch | None = None
        destination_batch: InventoryBatch | None = None
        if line.batch_id is not None:
            source_batch = await session.get(InventoryBatch, line.batch_id)
            assert source_batch is not None
            destination_batch = InventoryBatch(
                id=uuid.uuid4(),
                inventory_item_id=item.id,
                batch_code=source_batch.batch_code,
                storage_location_id=transfer.destination_location_id,
                supplier_id=source_batch.supplier_id,
                received_quantity=line.quantity,
                # Zero, not `line.quantity` — the `transfer_in` movement
                # posted below is this batch's sole writer for
                # `remaining_quantity` (see receipts.post_receipt's
                # identical fix for the full explanation).
                remaining_quantity=ZERO,
                received_at=now,
                manufactured_at=source_batch.manufactured_at,
                expires_at=source_batch.expires_at,
                unit_cost_minor=source_batch.unit_cost_minor,
                status="active",
                created_by=actor.id,
            )
            session.add(destination_batch)
            await session.flush()
            line.destination_batch_id = destination_batch.id

        out_movement = await ledger.post_movement(
            session,
            item=item,
            location=source,
            movement_type="transfer_out",
            quantity=line.quantity,
            batch=source_batch,
            actor_id=actor.id,
            occurred_at=now,
            reason=f"Transfer {transfer.transfer_number} to {destination.name}",
            reference_type="stock_transfer_item",
            reference_id=line.id,
        )
        await ledger.post_movement(
            session,
            item=item,
            location=destination,
            movement_type="transfer_in",
            quantity=line.quantity,
            batch=destination_batch,
            actor_id=actor.id,
            occurred_at=now,
            reason=f"Transfer {transfer.transfer_number} from {source.name}",
            reference_type="stock_transfer_item",
            reference_id=line.id,
            source_movement_id=out_movement.id,
            unit_cost_minor=(
                source_batch.unit_cost_minor
                if source_batch is not None
                else item.average_unit_cost_minor
            ),
        )

    transfer.status = "posted"
    transfer.posted_by = actor.id
    transfer.posted_at = now
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.transfer.posted",
        target_type="stock_transfer",
        target_id=transfer.id,
        request=request,
        safe_metadata={
            "transfer_number": transfer.transfer_number,
            "source_location_id": str(transfer.source_location_id),
            "destination_location_id": str(transfer.destination_location_id),
            "line_count": len(items),
        },
    )
    await record_domain_event(
        session,
        event_type="inventory.transfer.posted",
        aggregate_type="stock_transfer",
        aggregate_id=transfer.id,
        payload={"transfer_id": str(transfer.id), "transfer_number": transfer.transfer_number},
    )
    return transfer


async def reverse_transfer(
    session: AsyncSession,
    *,
    actor: StaffUser,
    transfer: StockTransfer,
    reason: str,
    request: Request | None,
) -> StockTransfer:
    if transfer.status != "posted":
        raise NotPostedError(
            f"Transfer {transfer.transfer_number} is not posted; nothing to reverse."
        )

    from app.db.models import StockMovement

    source = await session.get(StorageLocation, transfer.source_location_id)
    destination = await session.get(StorageLocation, transfer.destination_location_id)
    assert source is not None and destination is not None
    items = (
        await session.scalars(
            select(StockTransferItem).where(StockTransferItem.transfer_id == transfer.id)
        )
    ).all()

    for line in items:
        item = await session.get(InventoryItem, line.inventory_item_id)
        assert item is not None
        movements = (
            await session.scalars(
                select(StockMovement).where(
                    StockMovement.reference_type == "stock_transfer_item",
                    StockMovement.reference_id == line.id,
                )
            )
        ).all()
        for movement in movements:
            location = source if movement.movement_type == "transfer_out" else destination
            batch_id = movement.batch_id
            batch = await session.get(InventoryBatch, batch_id) if batch_id else None
            await ledger.reverse_movement(
                session,
                original=movement,
                item=item,
                location=location,
                actor_id=actor.id,
                reason=f"Reversal of {transfer.transfer_number}: {reason}",
                batch=batch,
            )

    transfer.status = "reversed"
    transfer.reversed_by = actor.id
    transfer.reversed_at = datetime.now(UTC)
    transfer.reversal_reason = reason
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.transfer.reversed",
        target_type="stock_transfer",
        target_id=transfer.id,
        request=request,
        safe_metadata={"transfer_number": transfer.transfer_number, "reason": reason},
    )
    return transfer
