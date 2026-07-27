"""Wastage recording — CORE_CRM_MODULES.md section 8.10.

Same single-step, immediately-posted shape as adjustments: an observed fact
recorded once, always a negative `wastage` stock movement.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    InventoryBatch,
    InventoryItem,
    StaffUser,
    StorageLocation,
    WastageRecord,
)
from app.inventory import ledger
from app.inventory.units import quantize_quantity
from app.outbox.service import record_domain_event


def generate_wastage_number() -> str:
    return f"WST-{uuid.uuid4().hex[:8].upper()}"


async def record_wastage(
    session: AsyncSession,
    *,
    actor: StaffUser,
    inventory_item_id: uuid.UUID,
    storage_location_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    quantity: Decimal,
    reason_category: str,
    reason: str,
    station: str | None,
    related_order_id: uuid.UUID | None,
    approved_by: uuid.UUID | None,
    idempotency_key: str | None,
    request: Request | None,
) -> WastageRecord:
    item = await session.get(InventoryItem, inventory_item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found."
        )
    location = await session.get(StorageLocation, storage_location_id)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Storage location not found."
        )
    batch: InventoryBatch | None = None
    if batch_id is not None:
        batch = await session.get(InventoryBatch, batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")

    now = datetime.now(UTC)
    wastage_number = generate_wastage_number()

    # Generated up front so it can be the movement's own `reference_id` at
    # post time — the append-only trigger on stock_movements forbids
    # updating `reference_id` after the fact (see adjustments.py's
    # create_adjustment for the full explanation).
    wastage_id = uuid.uuid4()
    movement = await ledger.post_movement(
        session,
        item=item,
        location=location,
        movement_type="wastage",
        quantity=quantize_quantity(quantity),
        batch=batch,
        actor_id=actor.id,
        occurred_at=now,
        reason=reason,
        reference_type="wastage_record",
        reference_id=wastage_id,
        idempotency_key=idempotency_key,
    )

    value_impact_minor: int | None = None
    if item.standard_cost_minor is not None:
        value_impact_minor = int(
            (quantize_quantity(quantity) * Decimal(item.standard_cost_minor)).to_integral_value()
        )

    record = WastageRecord(
        id=wastage_id,
        wastage_number=wastage_number,
        inventory_item_id=inventory_item_id,
        storage_location_id=storage_location_id,
        batch_id=batch_id,
        quantity=quantize_quantity(quantity),
        reason_category=reason_category,
        reason=reason,
        station=station,
        related_order_id=related_order_id,
        value_impact_minor=value_impact_minor,
        movement_id=movement.id,
        recorded_by=actor.id,
        approved_by=approved_by,
        approved_at=now if approved_by is not None else None,
    )
    session.add(record)
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.wastage.recorded",
        target_type="wastage_record",
        target_id=record.id,
        request=request,
        safe_metadata={
            "wastage_number": record.wastage_number,
            "quantity": str(record.quantity),
            "reason_category": reason_category,
            "value_impact_minor": value_impact_minor,
        },
    )
    await record_domain_event(
        session,
        event_type="inventory.wastage.recorded",
        aggregate_type="wastage_record",
        aggregate_id=record.id,
        payload={"wastage_id": str(record.id), "inventory_item_id": str(inventory_item_id)},
    )
    return record
