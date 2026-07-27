"""The append-only stock ledger and its balance projection.

**This is the only module permitted to insert into `stock_movements` or
mutate `stock_balances`.** Every other inventory service posts stock through
`post_movement`, which is what makes the invariants in this phase's
instruction enforceable in one place:

  - "Every stock change must create an append-only stock movement."
  - "Never change stock silently."
  - the balance projection "must be transactionally updated with the ledger"
    and "must never become an independent source of truth".

Sign convention (also recorded in DATABASE_AND_API.md section 9.8):
`stock_movements.quantity_delta` is signed, always in the item's base unit.
Positive adds to on-hand, negative removes from it. The two reservation types
are the sole exception — they carry a positive magnitude, set
`affects_on_hand = False`, and move quantity between reserved and available
on the same balance row without changing on-hand at all. A database CHECK
constraint enforces that pairing so a caller cannot get it wrong.

Rows are locked with `SELECT ... FOR UPDATE` before being adjusted, so two
concurrent transactions touching the same item/location serialize rather than
interleaving a read-modify-write and losing one of the two deltas.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    InventoryBatch,
    InventoryItem,
    StockBalance,
    StockMovement,
    StorageLocation,
)
from app.db.models.inventory_item import DERIVED_STOCK_STATUSES
from app.db.models.stock_movement import (
    INBOUND_MOVEMENT_TYPES,
    OUTBOUND_MOVEMENT_TYPES,
    RESERVATION_MOVEMENT_TYPES,
)
from app.inventory.errors import (
    DuplicateIdempotencyKeyError,
    InsufficientStockError,
    NegativeStockNotAllowedError,
    ReservationMismatchError,
)
from app.inventory.units import quantize_quantity

ZERO = Decimal("0.000")


def generate_movement_number() -> str:
    return f"MOV-{uuid.uuid4().hex[:10].upper()}"


async def find_by_idempotency_key(
    session: AsyncSession, idempotency_key: str
) -> StockMovement | None:
    """Look up an existing movement by idempotency key.

    Callers use this to make a repeated operation a no-op instead of a second
    deduction (this phase's rule: "Repeated requests must not double-deduct
    or double-add stock").
    """
    result = await session.scalar(
        select(StockMovement).where(StockMovement.idempotency_key == idempotency_key)
    )
    return result


async def _lock_balance(
    session: AsyncSession,
    *,
    inventory_item_id: uuid.UUID,
    storage_location_id: uuid.UUID,
    batch_id: uuid.UUID | None,
    allows_negative: bool,
) -> StockBalance:
    """Fetch-or-create the balance row for a coordinate, locked for update.

    `batch_id IS NULL` must be matched with `IS NULL` rather than `= NULL`,
    which is why this is not a single generic filter — a `== None` comparison
    in SQL never matches and would silently create duplicate non-batch rows
    on every movement.
    """
    stmt = select(StockBalance).where(
        StockBalance.inventory_item_id == inventory_item_id,
        StockBalance.storage_location_id == storage_location_id,
        StockBalance.batch_id == batch_id
        if batch_id is not None
        else StockBalance.batch_id.is_(None),
    )
    balance = await session.scalar(stmt.with_for_update())
    if balance is not None:
        # Keep the mirrored policy flag current if the location's policy
        # changed since this row was created.
        if balance.allows_negative != allows_negative:
            balance.allows_negative = allows_negative
        return balance

    balance = StockBalance(
        id=uuid.uuid4(),
        inventory_item_id=inventory_item_id,
        storage_location_id=storage_location_id,
        batch_id=batch_id,
        on_hand_quantity=ZERO,
        reserved_quantity=ZERO,
        allows_negative=allows_negative,
    )
    session.add(balance)
    await session.flush()
    return balance


async def post_movement(
    session: AsyncSession,
    *,
    item: InventoryItem,
    location: StorageLocation,
    movement_type: str,
    quantity: Decimal,
    batch: InventoryBatch | None = None,
    actor_id: uuid.UUID | None,
    occurred_at: datetime | None = None,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: uuid.UUID | None = None,
    source_movement_id: uuid.UUID | None = None,
    unit_cost_minor: int | None = None,
    entered_unit_id: uuid.UUID | None = None,
    entered_quantity: Decimal | None = None,
    idempotency_key: str | None = None,
    metadata: dict[str, Any] | None = None,
    is_increase: bool | None = None,
) -> StockMovement:
    """Post one movement and update the projection, atomically.

    `quantity` is always a POSITIVE magnitude in the item's base unit; the
    sign is derived from `movement_type`. Callers therefore cannot
    accidentally double-negate a decrease, which is the classic ledger bug
    (a negative quantity passed for a `negative_adjustment`).

    `is_increase` is required, and only meaningful, for movement types whose
    direction is not fixed by the type itself — currently only
    `stock_count_adjustment`, since a physical count can find either more or
    less stock than expected. Every other movement type's direction is
    determined entirely by `movement_type` and passing `is_increase` for one
    of them is a caller error.

    Raises rather than clamping when a decrease would drive on-hand below
    zero, unless the location explicitly allows negative stock — this
    phase's rule that "negative adjustments must not create invalid negative
    stock unless documented policy allows it".
    """
    if quantity <= ZERO:
        raise ValueError(
            f"post_movement expects a positive magnitude; got {quantity} "
            f"for {movement_type}. The sign is derived from the movement type."
        )

    quantity = quantize_quantity(quantity)
    now = occurred_at or datetime.now(UTC)

    if idempotency_key is not None:
        existing = await find_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            raise DuplicateIdempotencyKeyError(
                f"A stock movement with idempotency key {idempotency_key!r} already exists "
                f"({existing.movement_number}); the operation was not applied twice."
            )

    is_reservation = movement_type in RESERVATION_MOVEMENT_TYPES
    if movement_type == "stock_count_adjustment":
        if is_increase is None:
            raise ValueError("stock_count_adjustment requires is_increase to be set.")
        signed_quantity = quantity if is_increase else -quantity
    elif is_reservation:
        signed_quantity = quantity
    elif movement_type in OUTBOUND_MOVEMENT_TYPES:
        signed_quantity = -quantity
    elif movement_type in INBOUND_MOVEMENT_TYPES:
        signed_quantity = quantity
    else:
        # `reversal` carries its own direction, decided by the caller
        # unwinding a specific original movement.
        if movement_type != "reversal":
            raise ValueError(f"Unknown movement type: {movement_type!r}")
        signed_quantity = quantity

    balance = await _lock_balance(
        session,
        inventory_item_id=item.id,
        storage_location_id=location.id,
        batch_id=batch.id if batch is not None else None,
        allows_negative=location.allows_negative_stock,
    )

    if is_reservation:
        if movement_type == "order_reservation":
            available = balance.on_hand_quantity - balance.reserved_quantity
            if quantity > available and not location.allows_negative_stock:
                raise InsufficientStockError(
                    f"{item.name}: {quantity} required at {location.name} but only "
                    f"{available} available ({balance.on_hand_quantity} on hand, "
                    f"{balance.reserved_quantity} already reserved)."
                )
            balance.reserved_quantity = quantize_quantity(balance.reserved_quantity + quantity)
        else:
            if quantity > balance.reserved_quantity:
                raise ReservationMismatchError(
                    f"{item.name}: cannot release {quantity} at {location.name} — only "
                    f"{balance.reserved_quantity} is reserved."
                )
            balance.reserved_quantity = quantize_quantity(balance.reserved_quantity - quantity)
    else:
        new_on_hand = quantize_quantity(balance.on_hand_quantity + signed_quantity)
        if new_on_hand < ZERO and not location.allows_negative_stock:
            raise NegativeStockNotAllowedError(
                f"{item.name}: {abs(signed_quantity)} would take stock at {location.name} "
                f"from {balance.on_hand_quantity} to {new_on_hand}. Negative stock is not "
                "permitted at this location."
            )
        balance.on_hand_quantity = new_on_hand
        # Reserved must not exceed on-hand after a decrease (this phase's
        # explicit invariant). A consumption that draws down reserved stock
        # releases the matching reservation itself; anything else that
        # strands reservations above on-hand is a bug we surface immediately
        # rather than persisting an impossible balance.
        if balance.reserved_quantity > balance.on_hand_quantity and not (
            location.allows_negative_stock
        ):
            raise ReservationMismatchError(
                f"{item.name} at {location.name}: {balance.reserved_quantity} is reserved but "
                f"only {balance.on_hand_quantity} would remain on hand. Release the "
                "reservation before removing this stock."
            )

    balance.last_movement_at = now

    total_value_minor: int | None = None
    if unit_cost_minor is not None:
        total_value_minor = int((quantity * Decimal(unit_cost_minor)).to_integral_value())

    movement = StockMovement(
        id=uuid.uuid4(),
        movement_number=generate_movement_number(),
        inventory_item_id=item.id,
        storage_location_id=location.id,
        batch_id=batch.id if batch is not None else None,
        movement_type=movement_type,
        quantity_delta=signed_quantity,
        entered_unit_id=entered_unit_id,
        entered_quantity=entered_quantity,
        affects_on_hand=not is_reservation,
        unit_cost_minor=unit_cost_minor,
        total_value_minor=total_value_minor,
        reference_type=reference_type,
        reference_id=reference_id,
        source_movement_id=source_movement_id,
        reason=reason,
        performed_by=actor_id,
        occurred_at=now,
        idempotency_key=idempotency_key,
        movement_metadata=metadata,
    )
    session.add(movement)

    # Batch remaining quantity is a projection of the same ledger, kept in
    # step here so it can never disagree with the balance row.
    if batch is not None and not is_reservation:
        batch.remaining_quantity = quantize_quantity(batch.remaining_quantity + signed_quantity)
        if batch.remaining_quantity <= ZERO and batch.status == "active":
            batch.status = "depleted"
        elif batch.remaining_quantity > ZERO and batch.status == "depleted":
            batch.status = "active"

    await session.flush()
    await refresh_item_rollup(session, item)
    return movement


async def reverse_movement(
    session: AsyncSession,
    *,
    original: StockMovement,
    item: InventoryItem,
    location: StorageLocation,
    actor_id: uuid.UUID | None,
    reason: str,
    batch: InventoryBatch | None = None,
    idempotency_key: str | None = None,
) -> StockMovement:
    """Post a compensating `reversal` movement for `original`.

    The original row is never edited beyond its two reversal-bookkeeping
    columns (the database trigger installed by the Phase 8 migration enforces
    exactly that), so the ledger keeps both the mistake and its correction —
    this phase's "No Destructive Ledger Editing" rule.
    """
    from app.inventory.errors import AlreadyReversedError

    if original.reversed_by_movement_id is not None:
        raise AlreadyReversedError(f"Movement {original.movement_number} was already reversed.")

    magnitude = abs(original.quantity_delta)
    balance = await _lock_balance(
        session,
        inventory_item_id=item.id,
        storage_location_id=location.id,
        batch_id=original.batch_id,
        allows_negative=location.allows_negative_stock,
    )

    if original.affects_on_hand:
        # Flip the original's sign.
        signed_quantity = -original.quantity_delta
        new_on_hand = quantize_quantity(balance.on_hand_quantity + signed_quantity)
        if new_on_hand < ZERO and not location.allows_negative_stock:
            raise NegativeStockNotAllowedError(
                f"Reversing {original.movement_number} would take {item.name} at "
                f"{location.name} to {new_on_hand}. That stock has already moved on; "
                "record an adjustment or wastage instead."
            )
        balance.on_hand_quantity = new_on_hand
        if batch is not None:
            batch.remaining_quantity = quantize_quantity(batch.remaining_quantity + signed_quantity)
    else:
        # Reversing a reservation returns the reserved quantity.
        signed_quantity = magnitude
        if original.movement_type == "order_reservation":
            if magnitude > balance.reserved_quantity:
                raise ReservationMismatchError(
                    f"Cannot reverse {original.movement_number}: only "
                    f"{balance.reserved_quantity} of {item.name} is reserved."
                )
            balance.reserved_quantity = quantize_quantity(balance.reserved_quantity - magnitude)
        else:
            balance.reserved_quantity = quantize_quantity(balance.reserved_quantity + magnitude)

    now = datetime.now(UTC)
    balance.last_movement_at = now

    reversal = StockMovement(
        id=uuid.uuid4(),
        movement_number=generate_movement_number(),
        inventory_item_id=item.id,
        storage_location_id=location.id,
        batch_id=original.batch_id,
        movement_type="reversal",
        quantity_delta=signed_quantity,
        affects_on_hand=original.affects_on_hand,
        unit_cost_minor=original.unit_cost_minor,
        total_value_minor=(
            -original.total_value_minor if original.total_value_minor is not None else None
        ),
        reference_type=original.reference_type,
        reference_id=original.reference_id,
        source_movement_id=original.id,
        reason=reason,
        performed_by=actor_id,
        occurred_at=now,
        idempotency_key=idempotency_key,
        movement_metadata={"reversed_movement_number": original.movement_number},
    )
    session.add(reversal)
    await session.flush()

    original.reversed_by_movement_id = reversal.id
    original.reversed_at = now
    await session.flush()
    await refresh_item_rollup(session, item)
    return reversal


def derive_stock_status(item: InventoryItem) -> str:
    """Derive `in_stock`/`low_stock`/`critical_stock`/`out_of_stock` from the
    item's just-recomputed roll-up against its own reorder settings.

    Only ever called for an item whose *current* status is one of the four
    derived states — an operator-set state (`quarantined`, `expired`,
    `damaged`, `under_count_review`, `discontinued`) is never overwritten by
    this pass, per `DERIVED_STOCK_STATUSES`' own contract.

    Critical is half of the reorder level: a documented, simple threshold
    rather than a second configurable field this phase does not ask for.
    """
    if item.current_stock <= ZERO:
        return "out_of_stock"
    if item.reorder_level > ZERO:
        if item.current_stock <= item.reorder_level / Decimal(2):
            return "critical_stock"
        if item.current_stock <= item.reorder_level:
            return "low_stock"
    return "in_stock"


async def refresh_item_rollup(session: AsyncSession, item: InventoryItem) -> None:
    """Recompute `inventory_items.current_stock`/`reserved_stock` (and, from
    those, `stock_status`) from the item's balance rows.

    These roll-up columns are all-location summaries and are never
    authoritative; recomputing them from the projection (rather than
    incrementing them alongside it) means they cannot drift independently.
    """
    row = (
        await session.execute(
            select(
                func.coalesce(func.sum(StockBalance.on_hand_quantity), 0),
                func.coalesce(func.sum(StockBalance.reserved_quantity), 0),
            ).where(StockBalance.inventory_item_id == item.id)
        )
    ).one()
    item.current_stock = quantize_quantity(Decimal(row[0]))
    item.reserved_stock = quantize_quantity(Decimal(row[1]))
    if item.stock_status in DERIVED_STOCK_STATUSES:
        item.stock_status = derive_stock_status(item)


async def available_quantity(
    session: AsyncSession,
    *,
    inventory_item_id: uuid.UUID,
    storage_location_id: uuid.UUID | None = None,
) -> Decimal:
    """`on_hand - reserved`, summed across locations unless one is named.

    Computed rather than stored, per the deliberate decision recorded on
    `StockBalance`: a third stored number could disagree with the two it is
    derived from.
    """
    stmt = select(
        func.coalesce(func.sum(StockBalance.on_hand_quantity - StockBalance.reserved_quantity), 0)
    ).where(StockBalance.inventory_item_id == inventory_item_id)
    if storage_location_id is not None:
        stmt = stmt.where(StockBalance.storage_location_id == storage_location_id)
    result = await session.scalar(stmt)
    return quantize_quantity(Decimal(result or 0))
