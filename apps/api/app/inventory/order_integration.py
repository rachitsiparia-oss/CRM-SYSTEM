"""Order-to-inventory integration.

Phase 7 deliberately deferred stock effects. This module wires them in
*around* the unmodified Phase 7 state machine (`app.orders.states`,
`app.orders.service.transition_order`) rather than inside it — the exact
model this phase's instruction asks for: "integrate safely without
weakening its validation."

**Lifecycle decision** (this phase's instruction: "First inspect the
canonical documentation for the approved lifecycle. Use the documented
lifecycle if it exists" — no canonical document defines one, so the
conservative default below is used and recorded here and in
DATABASE_AND_API.md section 9.8):

  - `confirmed`  -> reserve. Rejects confirmation with `InsufficientStockError`
    if any tracked ingredient cannot be reserved; no override policy is
    documented, so this project applies no exception.
  - `preparing`  -> consume. Releases the matching reservation and deducts
    on-hand in the same operation, replaying the exact batch allocation
    decided at reservation time (not re-allocating), so consumption can
    never draw from a different batch than what was reserved.
  - `cancelled` from a state with an open reservation -> release, no
    on-hand change.
  - `cancelled` from a state that already consumed -> stock is NOT
    restored. `post_consumption_note` records that an operational decision
    (a controlled return via `create_adjustment`, or `record_wastage`) is
    outstanding — this phase's explicit rule against automating physical
    stock restoration after preparation has begun.
  - `completed` -> no inventory effect. Consumption already happened at
    `preparing`; this transition only marks the order done.

Phase 7's own transition table (`app.orders.states.ALLOWED_TRANSITIONS`)
only permits `cancelled` from `pending_confirmation`, `preparing`, and
`ready` — never from `confirmed`. In practice this means the
"cancel while reserved but not yet consumed" branch above is reachable only
from `pending_confirmation` (where nothing was ever reserved, since
reservation happens on `confirmed`) and is otherwise dormant; it is still
implemented correctly and unconditionally, both because the instruction
requires it and because a future phase could widen the transition table.

**Idempotency**: every function is a no-op if `OrderInventoryState.state`
already reflects the requested outcome — `UNIQUE(order_id)` plus the state
check together mean a retried request, a duplicate webhook, or a second
call from a race can never double-reserve or double-consume (this phase's
explicit requirement).

**Product without a recipe**: this phase's instruction validates recipes
only "where stock tracking is required." No `is_inventory_tracked` flag
exists on `Product` (Phase 6 scope), so the presence of an active resolved
recipe *is* that flag here: an order line for a product with no recipe is
treated as not inventory-tracked and skipped, not an error. Recorded as an
implementation decision in DATABASE_AND_API.md section 9.8.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    InventoryBatch,
    InventoryItem,
    Order,
    OrderInventoryState,
    OrderItem,
    RecipeItem,
    StaffUser,
    StorageLocation,
)
from app.inventory import allocation, ledger, recipes
from app.inventory.errors import InactiveRecipeError, InvalidLocationError
from app.inventory.units import quantize_quantity
from app.outbox.service import record_domain_event

ZERO = Decimal("0.000")


async def _get_or_create_state(session: AsyncSession, order: Order) -> OrderInventoryState:
    state = await session.scalar(
        select(OrderInventoryState).where(OrderInventoryState.order_id == order.id)
    )
    if state is not None:
        return state
    state = OrderInventoryState(id=uuid.uuid4(), order_id=order.id, state="pending")
    session.add(state)
    await session.flush()
    return state


def _effective_ingredient_quantity(recipe_item: RecipeItem, order_quantity: int) -> Decimal:
    """Per-unit-ordered ingredient need, inflated by the recipe's per-
    ingredient waste factor — the same formula `app.inventory.recipes` uses
    for costing, so the physical and financial models never disagree about
    how much of an ingredient one sellable unit actually uses.
    """
    waste_divisor = Decimal(1) - recipe_item.waste_factor
    per_unit = (
        recipe_item.base_quantity / waste_divisor
        if waste_divisor > ZERO
        else recipe_item.base_quantity
    )
    return quantize_quantity(per_unit * Decimal(order_quantity))


async def reserve_stock_for_order(
    session: AsyncSession, *, actor: StaffUser, order: Order, request: Request | None
) -> OrderInventoryState:
    state = await _get_or_create_state(session, order)
    if state.state != "pending":
        return state  # Already reserved/consumed/released/skipped — no-op.

    order_items = (
        await session.scalars(
            select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.status == "active")
        )
    ).all()

    now = datetime.now(UTC)
    lines_snapshot: list[dict[str, Any]] = []
    has_trackable_line = False
    estimated_cost_minor = 0

    for order_item in order_items:
        if order_item.product_id is None:
            continue
        recipe = await recipes.resolve_recipe(
            session,
            product_id=order_item.product_id,
            variant_id=order_item.variant_id,
            as_of=now,
        )
        if recipe is None:
            continue  # Not inventory-tracked — see module docstring.
        if not recipe.is_active:
            raise InactiveRecipeError(
                f"Recipe {recipe.recipe_code} for order item {order_item.id} is not active."
            )
        has_trackable_line = True

        recipe_items = (
            await session.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id))
        ).all()

        ingredients_snapshot: list[dict[str, Any]] = []
        for recipe_item in recipe_items:
            item = await session.get(InventoryItem, recipe_item.inventory_item_id)
            assert item is not None
            required = _effective_ingredient_quantity(recipe_item, order_item.quantity)
            location_id = recipe_item.storage_location_id or item.default_location_id
            if location_id is None:
                raise InvalidLocationError(
                    f"{item.name} has no storage location configured (neither the recipe "
                    "line nor the item itself names one)."
                )
            location = await session.get(StorageLocation, location_id)
            assert location is not None

            batch_allocations: list[dict[str, str]] = []
            if item.requires_batch_tracking:
                allocations = await allocation.allocate_batches(
                    session,
                    inventory_item_id=item.id,
                    storage_location_id=location_id,
                    quantity=required,
                )
                for entry in allocations:
                    await ledger.post_movement(
                        session,
                        item=item,
                        location=location,
                        movement_type="order_reservation",
                        quantity=entry.quantity,
                        batch=entry.batch,
                        actor_id=actor.id,
                        occurred_at=now,
                        reason=f"Reserved for order {order.order_number}",
                        reference_type="order",
                        reference_id=order.id,
                        idempotency_key=f"order-reserve-{order.id}-{entry.batch.id}",
                    )
                    batch_allocations.append(
                        {"batch_id": str(entry.batch.id), "quantity": str(entry.quantity)}
                    )
            else:
                await ledger.post_movement(
                    session,
                    item=item,
                    location=location,
                    movement_type="order_reservation",
                    quantity=required,
                    batch=None,
                    actor_id=actor.id,
                    occurred_at=now,
                    reason=f"Reserved for order {order.order_number}",
                    reference_type="order",
                    reference_id=order.id,
                    idempotency_key=f"order-reserve-{order.id}-{item.id}-{location_id}",
                )

            unit_cost_minor = item.standard_cost_minor or item.latest_purchase_cost_minor
            if unit_cost_minor is not None:
                estimated_cost_minor += int(
                    (required * Decimal(unit_cost_minor)).to_integral_value()
                )

            ingredients_snapshot.append(
                {
                    "recipe_item_id": str(recipe_item.id),
                    "inventory_item_id": str(item.id),
                    "inventory_item_name": item.name,
                    "location_id": str(location_id),
                    "required_base_quantity": str(required),
                    "batch_allocations": batch_allocations or None,
                }
            )

        lines_snapshot.append(
            {
                "order_item_id": str(order_item.id),
                "product_id": str(order_item.product_id),
                "variant_id": str(order_item.variant_id) if order_item.variant_id else None,
                "recipe_id": str(recipe.id),
                "recipe_code": recipe.recipe_code,
                "quantity_ordered": order_item.quantity,
                "ingredients": ingredients_snapshot,
            }
        )

    state.state = "reserved" if has_trackable_line else "skipped"
    state.reserved_at = now
    state.consumption_snapshot = {"resolved_at": now.isoformat(), "lines": lines_snapshot}
    state.estimated_cost_minor = estimated_cost_minor if has_trackable_line else None
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.order.reserved",
        target_type="order",
        target_id=order.id,
        request=request,
        safe_metadata={
            "state": state.state,
            "line_count": len(lines_snapshot),
            "estimated_cost_minor": state.estimated_cost_minor,
        },
    )
    if has_trackable_line:
        await record_domain_event(
            session,
            event_type="inventory.order.reserved",
            aggregate_type="order",
            aggregate_id=order.id,
            payload={"order_id": str(order.id), "order_number": order.order_number},
        )
    return state


async def consume_stock_for_order(
    session: AsyncSession, *, actor: StaffUser, order: Order, request: Request | None
) -> OrderInventoryState:
    state = await _get_or_create_state(session, order)
    if state.state in ("consumed", "released"):
        return state  # Idempotent no-op.
    if state.state == "pending":
        # Confirmation never ran a reservation (e.g. the order skipped
        # straight to preparing in a test or a future workflow) — there is
        # nothing to consume.
        state.state = "skipped"
        await session.flush()
        return state
    if state.state == "skipped":
        return state

    now = datetime.now(UTC)
    snapshot = state.consumption_snapshot or {"lines": []}
    consumed_cost_minor = 0

    for line in snapshot.get("lines", []):
        for ingredient in line["ingredients"]:
            item = await session.get(InventoryItem, uuid.UUID(ingredient["inventory_item_id"]))
            location = await session.get(StorageLocation, uuid.UUID(ingredient["location_id"]))
            assert item is not None and location is not None

            batch_allocations = ingredient.get("batch_allocations")
            if batch_allocations:
                for entry in batch_allocations:
                    batch = await session.get(InventoryBatch, uuid.UUID(entry["batch_id"]))
                    quantity = Decimal(entry["quantity"])
                    await ledger.post_movement(
                        session,
                        item=item,
                        location=location,
                        movement_type="reservation_release",
                        quantity=quantity,
                        batch=batch,
                        actor_id=actor.id,
                        occurred_at=now,
                        reason=f"Consumption for order {order.order_number}",
                        reference_type="order",
                        reference_id=order.id,
                        idempotency_key=f"order-release-{order.id}-{entry['batch_id']}",
                    )
                    unit_cost_minor = (
                        batch.unit_cost_minor if batch is not None else item.standard_cost_minor
                    )
                    await ledger.post_movement(
                        session,
                        item=item,
                        location=location,
                        movement_type="order_consumption",
                        quantity=quantity,
                        batch=batch,
                        actor_id=actor.id,
                        occurred_at=now,
                        reason=f"Consumed for order {order.order_number}",
                        reference_type="order",
                        reference_id=order.id,
                        unit_cost_minor=unit_cost_minor,
                        idempotency_key=f"order-consume-{order.id}-{entry['batch_id']}",
                    )
                    if unit_cost_minor is not None:
                        consumed_cost_minor += int(
                            (quantity * Decimal(unit_cost_minor)).to_integral_value()
                        )
            else:
                quantity = Decimal(ingredient["required_base_quantity"])
                await ledger.post_movement(
                    session,
                    item=item,
                    location=location,
                    movement_type="reservation_release",
                    quantity=quantity,
                    batch=None,
                    actor_id=actor.id,
                    occurred_at=now,
                    reason=f"Consumption for order {order.order_number}",
                    reference_type="order",
                    reference_id=order.id,
                    idempotency_key=f"order-release-{order.id}-{item.id}-{location.id}",
                )
                unit_cost_minor = item.standard_cost_minor or item.latest_purchase_cost_minor
                await ledger.post_movement(
                    session,
                    item=item,
                    location=location,
                    movement_type="order_consumption",
                    quantity=quantity,
                    batch=None,
                    actor_id=actor.id,
                    occurred_at=now,
                    reason=f"Consumed for order {order.order_number}",
                    reference_type="order",
                    reference_id=order.id,
                    unit_cost_minor=unit_cost_minor,
                    idempotency_key=f"order-consume-{order.id}-{item.id}-{location.id}",
                )
                if unit_cost_minor is not None:
                    consumed_cost_minor += int(
                        (quantity * Decimal(unit_cost_minor)).to_integral_value()
                    )

    state.state = "consumed"
    state.consumed_at = now
    state.consumed_cost_minor = consumed_cost_minor or None
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.order.consumed",
        target_type="order",
        target_id=order.id,
        request=request,
        safe_metadata={"consumed_cost_minor": state.consumed_cost_minor},
    )
    await record_domain_event(
        session,
        event_type="inventory.order.consumed",
        aggregate_type="order",
        aggregate_id=order.id,
        payload={"order_id": str(order.id), "order_number": order.order_number},
    )
    return state


async def release_stock_for_order(
    session: AsyncSession, *, actor: StaffUser, order: Order, request: Request | None
) -> OrderInventoryState:
    state = await _get_or_create_state(session, order)
    now = datetime.now(UTC)

    if state.state == "reserved":
        snapshot = state.consumption_snapshot or {"lines": []}
        for line in snapshot.get("lines", []):
            for ingredient in line["ingredients"]:
                item = await session.get(InventoryItem, uuid.UUID(ingredient["inventory_item_id"]))
                location = await session.get(StorageLocation, uuid.UUID(ingredient["location_id"]))
                assert item is not None and location is not None
                batch_allocations = ingredient.get("batch_allocations")
                if batch_allocations:
                    for entry in batch_allocations:
                        batch = await session.get(InventoryBatch, uuid.UUID(entry["batch_id"]))
                        await ledger.post_movement(
                            session,
                            item=item,
                            location=location,
                            movement_type="reservation_release",
                            quantity=Decimal(entry["quantity"]),
                            batch=batch,
                            actor_id=actor.id,
                            occurred_at=now,
                            reason=f"Released — order {order.order_number} cancelled",
                            reference_type="order",
                            reference_id=order.id,
                            idempotency_key=f"order-cancel-release-{order.id}-{entry['batch_id']}",
                        )
                else:
                    await ledger.post_movement(
                        session,
                        item=item,
                        location=location,
                        movement_type="reservation_release",
                        quantity=Decimal(ingredient["required_base_quantity"]),
                        batch=None,
                        actor_id=actor.id,
                        occurred_at=now,
                        reason=f"Released — order {order.order_number} cancelled",
                        reference_type="order",
                        reference_id=order.id,
                        idempotency_key=f"order-cancel-release-{order.id}-{item.id}-{location.id}",
                    )
        state.state = "released"
        state.released_at = now
        await session.flush()
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="inventory.order.released",
            target_type="order",
            target_id=order.id,
            request=request,
            safe_metadata={"order_number": order.order_number},
        )
        await record_domain_event(
            session,
            event_type="inventory.order.released",
            aggregate_type="order",
            aggregate_id=order.id,
            payload={"order_id": str(order.id), "order_number": order.order_number},
        )
    elif state.state == "consumed":
        # This phase's explicit rule: never automate physical stock
        # restoration after preparation has begun. The note is the durable
        # record that a human decision (return or wastage) is outstanding.
        state.post_consumption_note = (
            f"Order {order.order_number} was cancelled after its ingredients were already "
            "consumed. Stock was not automatically restored — record a positive adjustment "
            "if any ingredients are recoverable, or record wastage otherwise."
        )
        await session.flush()
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="inventory.order.cancelled_after_consumption",
            target_type="order",
            target_id=order.id,
            request=request,
            safe_metadata={"note": state.post_consumption_note},
        )
    # "pending" / "skipped": nothing was ever reserved or consumed — no-op.
    return state


async def transition_order_with_inventory(
    session: AsyncSession,
    *,
    actor: StaffUser,
    order: Order,
    new_status: str,
    reason: str | None,
    request: Request | None,
) -> None:
    """The router's entry point: runs the inventory side effect for a status
    transition around the unmodified Phase 7 `transition_order`.

    Reservation happens *before* calling `transition_order` for `confirmed`,
    so an `InsufficientStockError` aborts the whole operation before the
    order's status ever changes (this phase's rule: "reject confirmation
    with a clear stock-shortage response if required stock is unavailable").
    Consumption and release happen after, since neither can fail in a way
    that should block the status change itself.
    """
    from app.orders import service as orders_service

    if new_status == "confirmed":
        await reserve_stock_for_order(session, actor=actor, order=order, request=request)

    await orders_service.transition_order(
        session, actor=actor, order=order, new_status=new_status, reason=reason, request=request
    )

    if new_status == "preparing":
        await consume_stock_for_order(session, actor=actor, order=order, request=request)
    elif new_status == "cancelled":
        await release_stock_for_order(session, actor=actor, order=order, request=request)
