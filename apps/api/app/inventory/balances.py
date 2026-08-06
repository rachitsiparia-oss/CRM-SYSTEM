"""Balance verification, drift detection, and controlled rebuild.

This phase's own instruction: "Provide an internal verification function that
recalculates balances from the ledger and detects drift. Do not silently fix
drift. Report it clearly and provide a controlled rebuild operation restricted
by permission."

So there are two deliberately separate entry points:

  `verify_balances`  — read-only. Recomputes every balance from
                       `stock_movements` and returns the discrepancies. Safe
                       to call from a health check or a report; changes
                       nothing.
  `rebuild_balances` — destructive-by-design. Rewrites the projection from
                       the ledger. Gated on `inventory.balances.rebuild`
                       (owner/GM only in the role matrix) and audited.

Splitting them is the point: a drifted projection is evidence of a bug, and
auto-healing it on read would erase that evidence.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import Request
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import InventoryItem, StaffUser, StockBalance, StockMovement, StorageLocation
from app.db.models.inventory_item import DERIVED_STOCK_STATUSES
from app.inventory.ledger import derive_stock_status
from app.inventory.units import quantize_quantity

ZERO = Decimal("0.000")


@dataclass(frozen=True)
class BalanceDrift:
    """One disagreement between the projection and the ledger."""

    inventory_item_id: uuid.UUID
    storage_location_id: uuid.UUID
    batch_id: uuid.UUID | None
    projected_on_hand: Decimal
    ledger_on_hand: Decimal

    @property
    def difference(self) -> Decimal:
        return quantize_quantity(self.projected_on_hand - self.ledger_on_hand)


async def _ledger_on_hand_by_coordinate(
    session: AsyncSession,
) -> dict[tuple[uuid.UUID, uuid.UUID, uuid.UUID | None], Decimal]:
    """Sum on-hand-affecting deltas per item/location/batch, in the database.

    Only `affects_on_hand` rows count: reservation movements deliberately do
    not change on-hand (see the sign convention in app.inventory.ledger), so
    including them would produce phantom drift on every reserved order.
    """
    rows = (
        await session.execute(
            select(
                StockMovement.inventory_item_id,
                StockMovement.storage_location_id,
                StockMovement.batch_id,
                func.coalesce(func.sum(StockMovement.quantity_delta), 0),
            )
            .where(StockMovement.affects_on_hand.is_(True))
            .group_by(
                StockMovement.inventory_item_id,
                StockMovement.storage_location_id,
                StockMovement.batch_id,
            )
        )
    ).all()
    return {(row[0], row[1], row[2]): quantize_quantity(Decimal(row[3])) for row in rows}


async def verify_balances(
    session: AsyncSession, *, inventory_item_id: uuid.UUID | None = None
) -> list[BalanceDrift]:
    """Recompute balances from the ledger and report any drift.

    Read-only. An empty list means the projection reconciles exactly with the
    ledger — which is the acceptance criterion CORE_CRM_MODULES.md section
    8.21 states ("current stock reconciles with movement history").
    """
    ledger_totals = await _ledger_on_hand_by_coordinate(session)

    stmt = select(StockBalance)
    if inventory_item_id is not None:
        stmt = stmt.where(StockBalance.inventory_item_id == inventory_item_id)
    balances = (await session.scalars(stmt)).all()

    drifts: list[BalanceDrift] = []
    seen: set[tuple[uuid.UUID, uuid.UUID, uuid.UUID | None]] = set()

    for balance in balances:
        key = (balance.inventory_item_id, balance.storage_location_id, balance.batch_id)
        seen.add(key)
        ledger_value = ledger_totals.get(key, ZERO)
        if quantize_quantity(balance.on_hand_quantity) != ledger_value:
            drifts.append(
                BalanceDrift(
                    inventory_item_id=balance.inventory_item_id,
                    storage_location_id=balance.storage_location_id,
                    batch_id=balance.batch_id,
                    projected_on_hand=quantize_quantity(balance.on_hand_quantity),
                    ledger_on_hand=ledger_value,
                )
            )

    # A coordinate the ledger knows about but the projection has no row for is
    # drift too — arguably the worse kind, since the stock is invisible.
    for key, ledger_value in ledger_totals.items():
        if key in seen or ledger_value == ZERO:
            continue
        if inventory_item_id is not None and key[0] != inventory_item_id:
            continue
        drifts.append(
            BalanceDrift(
                inventory_item_id=key[0],
                storage_location_id=key[1],
                batch_id=key[2],
                projected_on_hand=ZERO,
                ledger_on_hand=ledger_value,
            )
        )

    return drifts


async def rebuild_balances(
    session: AsyncSession,
    *,
    actor: StaffUser,
    request: Request | None = None,
    inventory_item_id: uuid.UUID | None = None,
) -> dict[str, int]:
    """Rewrite the balance projection from the ledger.

    Reserved quantities are recomputed from the ledger too — the running sum
    of `order_reservation` minus `reservation_release` per coordinate — so a
    rebuild restores both halves of every balance row, not just on-hand.

    The caller is responsible for the permission check
    (`inventory.balances.rebuild`); this function records the audit event
    because the rebuild itself is the sensitive act.
    """
    ledger_totals = await _ledger_on_hand_by_coordinate(session)

    reservation_rows = (
        await session.execute(
            select(
                StockMovement.inventory_item_id,
                StockMovement.storage_location_id,
                StockMovement.batch_id,
                func.coalesce(
                    func.sum(
                        case(
                            (
                                StockMovement.movement_type == "order_reservation",
                                StockMovement.quantity_delta,
                            ),
                            (
                                StockMovement.movement_type == "reservation_release",
                                -StockMovement.quantity_delta,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .where(StockMovement.affects_on_hand.is_(False))
            .group_by(
                StockMovement.inventory_item_id,
                StockMovement.storage_location_id,
                StockMovement.batch_id,
            )
        )
    ).all()
    reserved_totals = {
        (row[0], row[1], row[2]): quantize_quantity(Decimal(row[3])) for row in reservation_rows
    }

    location_policy = {
        loc.id: loc.allows_negative_stock
        for loc in (await session.scalars(select(StorageLocation))).all()
    }

    stmt = select(StockBalance)
    if inventory_item_id is not None:
        stmt = stmt.where(StockBalance.inventory_item_id == inventory_item_id)
    existing = {
        (b.inventory_item_id, b.storage_location_id, b.batch_id): b
        for b in (await session.scalars(stmt.with_for_update())).all()
    }

    coordinates = set(ledger_totals) | set(reserved_totals) | set(existing)
    if inventory_item_id is not None:
        coordinates = {c for c in coordinates if c[0] == inventory_item_id}

    updated = 0
    created = 0
    now = datetime.now(UTC)

    for key in coordinates:
        on_hand = ledger_totals.get(key, ZERO)
        reserved = reserved_totals.get(key, ZERO)
        # A reservation can outlive the stock it pointed at only if something
        # went wrong upstream; clamping here would hide it, so the rebuild
        # keeps the ledger's answer and the CHECK constraint refuses the row
        # if it is genuinely impossible.
        balance = existing.get(key)
        if balance is None:
            if on_hand == ZERO and reserved == ZERO:
                continue
            balance = StockBalance(
                id=uuid.uuid4(),
                inventory_item_id=key[0],
                storage_location_id=key[1],
                batch_id=key[2],
                allows_negative=location_policy.get(key[1], False),
            )
            session.add(balance)
            created += 1
        else:
            updated += 1
        balance.on_hand_quantity = on_hand
        balance.reserved_quantity = reserved
        balance.allows_negative = location_policy.get(key[1], False)
        balance.last_movement_at = balance.last_movement_at or now

    await session.flush()

    items_stmt = select(InventoryItem)
    totals_stmt = select(
        StockBalance.inventory_item_id,
        func.coalesce(func.sum(StockBalance.on_hand_quantity), 0),
        func.coalesce(func.sum(StockBalance.reserved_quantity), 0),
    ).group_by(StockBalance.inventory_item_id)
    if inventory_item_id is not None:
        items_stmt = items_stmt.where(InventoryItem.id == inventory_item_id)
        totals_stmt = totals_stmt.where(StockBalance.inventory_item_id == inventory_item_id)
    # One grouped aggregate for every item instead of one query per item —
    # a full-catalog rebuild (no inventory_item_id filter) previously issued
    # N+1 queries here.
    item_totals = {row[0]: (row[1], row[2]) for row in (await session.execute(totals_stmt)).all()}
    for item in (await session.scalars(items_stmt)).all():
        on_hand_total, reserved_total = item_totals.get(item.id, (0, 0))
        item.current_stock = quantize_quantity(Decimal(on_hand_total))
        item.reserved_stock = quantize_quantity(Decimal(reserved_total))
        if item.stock_status in DERIVED_STOCK_STATUSES:
            item.stock_status = derive_stock_status(item)

    summary = {"coordinates": len(coordinates), "created": created, "updated": updated}
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.balances_rebuilt",
        target_type="inventory",
        target_id=inventory_item_id,
        request=request,
        safe_metadata=summary,
    )
    await session.flush()
    return summary
