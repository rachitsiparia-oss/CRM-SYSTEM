"""Manual stock adjustments — CORE_CRM_MODULES.md section 8.9.

A single-step, immediately-posted correction (see StockAdjustment's
docstring for why there is no draft state). Approval is enforced by the
router via `inventory.adjustments.approve`, not here; this module records
whichever actor is passed as `approved_by`.
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
    StockAdjustment,
    StorageLocation,
)
from app.inventory import ledger
from app.inventory.units import quantize_quantity
from app.outbox.service import record_domain_event


def generate_adjustment_number() -> str:
    return f"ADJ-{uuid.uuid4().hex[:8].upper()}"


async def create_adjustment(
    session: AsyncSession,
    *,
    actor: StaffUser,
    inventory_item_id: uuid.UUID,
    storage_location_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    direction: str,
    quantity: Decimal,
    reason_category: str,
    reason: str,
    approved_by: uuid.UUID | None,
    idempotency_key: str | None,
    request: Request | None,
) -> StockAdjustment:
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

    movement_type = "positive_adjustment" if direction == "increase" else "negative_adjustment"
    now = datetime.now(UTC)

    # Generated up front (this codebase's ids are always client-generated
    # uuid4s, never DB defaults) so it can be passed as the movement's own
    # `reference_id` at post time — the append-only trigger on
    # stock_movements forbids updating `reference_id` after the fact, so a
    # "post now, backfill the reference once the parent row exists" order
    # is not an option here.
    adjustment_id = uuid.uuid4()
    adjustment_number = generate_adjustment_number()
    movement = await ledger.post_movement(
        session,
        item=item,
        location=location,
        movement_type=movement_type,
        quantity=quantize_quantity(quantity),
        batch=batch,
        actor_id=actor.id,
        occurred_at=now,
        reason=reason,
        reference_type="stock_adjustment",
        reference_id=adjustment_id,
        idempotency_key=idempotency_key,
    )

    value_impact_minor: int | None = None
    if item.standard_cost_minor is not None:
        value_impact_minor = int(
            (quantize_quantity(quantity) * Decimal(item.standard_cost_minor)).to_integral_value()
        )

    adjustment = StockAdjustment(
        id=adjustment_id,
        adjustment_number=adjustment_number,
        inventory_item_id=inventory_item_id,
        storage_location_id=storage_location_id,
        batch_id=batch_id,
        direction=direction,
        quantity=quantize_quantity(quantity),
        reason_category=reason_category,
        reason=reason,
        value_impact_minor=value_impact_minor,
        movement_id=movement.id,
        recorded_by=actor.id,
        approved_by=approved_by,
        approved_at=now if approved_by is not None else None,
    )
    session.add(adjustment)
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.adjustment.posted",
        target_type="stock_adjustment",
        target_id=adjustment.id,
        request=request,
        safe_metadata={
            "adjustment_number": adjustment.adjustment_number,
            "direction": direction,
            "quantity": str(adjustment.quantity),
            "reason_category": reason_category,
            "value_impact_minor": value_impact_minor,
            "approved_by": str(approved_by) if approved_by else None,
        },
    )
    await record_domain_event(
        session,
        event_type="inventory.adjustment.posted",
        aggregate_type="stock_adjustment",
        aggregate_id=adjustment.id,
        payload={
            "adjustment_id": str(adjustment.id),
            "inventory_item_id": str(inventory_item_id),
            "direction": direction,
        },
    )
    return adjustment
