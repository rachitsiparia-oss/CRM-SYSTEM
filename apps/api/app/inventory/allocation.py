"""Deterministic batch allocation.

This phase's own instruction: "For expiry-tracked stock, prefer FEFO (first
expiry, first out). For non-expiry stock... if documentation is silent, use
oldest received batch first... Do not consume expired batches."

Only consulted for items with `requires_batch_tracking` — a non-batch-tracked
item has no batches to choose between, and its stock is posted directly
against `batch=None`.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InventoryBatch
from app.inventory.errors import ExpiredBatchError, InsufficientStockError
from app.inventory.units import quantize_quantity

ZERO = Decimal("0.000")


@dataclass(frozen=True)
class BatchAllocation:
    batch: InventoryBatch
    quantity: Decimal


async def allocate_batches(
    session: AsyncSession,
    *,
    inventory_item_id: uuid.UUID,
    storage_location_id: uuid.UUID,
    quantity: Decimal,
    as_of: date | None = None,
) -> list[BatchAllocation]:
    """Select which batches to draw `quantity` from at one location.

    Ordering: batches with a set expiry date first, soonest expiry first
    (FEFO); batches with no expiry date after, oldest `received_at` first.
    This single ORDER BY expresses both documented rules at once — an
    expiry-tracked item's batches all have `expires_at` set and sort by
    FEFO; a batch-tracked-but-not-expiry-tracked item's batches all have
    `expires_at IS NULL` and sort oldest-received-first.

    Raises `ExpiredBatchError` if satisfying the request would require
    drawing from a batch whose `expires_at` has already passed, and
    `InsufficientStockError` if the location's active batches do not sum to
    enough remaining quantity — never partially allocates and never falls
    back to a batch that should be excluded.
    """
    quantity = quantize_quantity(quantity)
    today = as_of or date.today()

    rows = (
        await session.scalars(
            select(InventoryBatch)
            .where(
                InventoryBatch.inventory_item_id == inventory_item_id,
                InventoryBatch.storage_location_id == storage_location_id,
                InventoryBatch.status == "active",
                InventoryBatch.remaining_quantity > ZERO,
            )
            .order_by(
                InventoryBatch.expires_at.is_(None),
                InventoryBatch.expires_at.asc(),
                InventoryBatch.received_at.asc(),
            )
            .with_for_update()
        )
    ).all()

    allocations: list[BatchAllocation] = []
    remaining = quantity
    for batch in rows:
        if remaining <= ZERO:
            break
        if batch.expires_at is not None and batch.expires_at < today:
            # An expired batch is never consumed, even if earlier (valid)
            # batches already satisfied the request — surfacing this instead
            # of silently skipping it keeps expired stock visible to staff
            # rather than quietly vanishing from the allocation.
            raise ExpiredBatchError(
                f"Batch {batch.batch_code} expired on {batch.expires_at} and cannot be "
                "allocated. Quarantine or write it off before continuing."
            )
        take = min(batch.remaining_quantity, remaining)
        allocations.append(BatchAllocation(batch=batch, quantity=take))
        remaining = quantize_quantity(remaining - take)

    if remaining > ZERO:
        raise InsufficientStockError(
            f"Only {quantity - remaining} of {quantity} requested is available across "
            "active, non-expired batches at this location."
        )

    return allocations
