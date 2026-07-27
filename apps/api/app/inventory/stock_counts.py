"""Physical stock-count sessions — CORE_CRM_MODULES.md section 8.11.

draft -> in_progress -> submitted -> approved (or cancelled from any
non-terminal state). Only `approve_count` touches the ledger: it posts one
`stock_count_adjustment` movement per non-zero variance line, in the
transaction that also marks the session approved.
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
    StockBalance,
    StockCount,
    StockCountLine,
    StorageLocation,
)
from app.inventory import ledger
from app.inventory.errors import InvalidCountStateError
from app.inventory.units import quantize_quantity
from app.outbox.service import record_domain_event

ZERO = Decimal("0.000")


def generate_count_number() -> str:
    return f"CNT-{uuid.uuid4().hex[:8].upper()}"


async def create_count(
    session: AsyncSession,
    *,
    actor: StaffUser,
    storage_location_id: uuid.UUID,
    scheduled_date: date | None,
    notes: str | None,
) -> StockCount:
    location = await session.get(StorageLocation, storage_location_id)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Storage location not found."
        )

    # A friendlier error than the database's partial-unique-index violation,
    # for the common case of a staff member not realizing a session is
    # already open (this phase's instruction: "prevent duplicate active
    # count sessions for the same location").
    existing = await session.scalar(
        select(StockCount).where(
            StockCount.storage_location_id == storage_location_id,
            StockCount.status.in_(("draft", "in_progress", "submitted")),
        )
    )
    if existing is not None:
        raise InvalidCountStateError(
            f"{location.name} already has an active count session "
            f"({existing.count_number}, {existing.status}). Complete or cancel it first."
        )

    count = StockCount(
        id=uuid.uuid4(),
        count_number=generate_count_number(),
        storage_location_id=storage_location_id,
        status="draft",
        scheduled_date=scheduled_date,
        notes=notes,
        created_by=actor.id,
    )
    session.add(count)
    await session.flush()
    return count


async def start_count(session: AsyncSession, *, actor: StaffUser, count: StockCount) -> StockCount:
    if count.status != "draft":
        raise InvalidCountStateError(
            f"Count {count.count_number} is {count.status}; only a draft count can be started."
        )

    # Snapshot expected stock: one line per non-batch balance row, plus one
    # per active batch, at this location — this phase's own instruction,
    # "freeze or snapshot expected stock" before counting begins, so a
    # variance stays meaningful even if other movements happen mid-count.
    balances = (
        await session.scalars(
            select(StockBalance).where(
                StockBalance.storage_location_id == count.storage_location_id,
                StockBalance.batch_id.is_(None),
            )
        )
    ).all()
    for balance in balances:
        session.add(
            StockCountLine(
                id=uuid.uuid4(),
                count_id=count.id,
                inventory_item_id=balance.inventory_item_id,
                batch_id=None,
                system_quantity=balance.on_hand_quantity,
            )
        )

    batches = (
        await session.scalars(
            select(InventoryBatch).where(
                InventoryBatch.storage_location_id == count.storage_location_id,
                InventoryBatch.status == "active",
                InventoryBatch.remaining_quantity > ZERO,
            )
        )
    ).all()
    for batch in batches:
        session.add(
            StockCountLine(
                id=uuid.uuid4(),
                count_id=count.id,
                inventory_item_id=batch.inventory_item_id,
                batch_id=batch.id,
                system_quantity=batch.remaining_quantity,
            )
        )

    count.status = "in_progress"
    count.started_at = datetime.now(UTC)
    count.counted_by = actor.id
    await session.flush()
    return count


async def record_count_line(
    session: AsyncSession,
    *,
    count: StockCount,
    line: StockCountLine,
    counted_quantity: Decimal,
    reason: str | None,
    notes: str | None,
) -> StockCountLine:
    if count.status != "in_progress":
        raise InvalidCountStateError(
            f"Count {count.count_number} is {count.status}; counts can only be entered "
            "while the session is in progress."
        )
    line.counted_quantity = quantize_quantity(counted_quantity)
    line.variance_quantity = quantize_quantity(line.counted_quantity - line.system_quantity)
    item = await session.get(InventoryItem, line.inventory_item_id)
    if item is not None and item.standard_cost_minor is not None:
        line.variance_value_minor = int(
            (line.variance_quantity * Decimal(item.standard_cost_minor)).to_integral_value()
        )
    line.reason = reason
    line.notes = notes
    await session.flush()
    return line


async def submit_count(
    session: AsyncSession, *, actor: StaffUser, count: StockCount, request: Request | None
) -> StockCount:
    if count.status != "in_progress":
        raise InvalidCountStateError(
            f"Count {count.count_number} is {count.status}; only an in-progress count can "
            "be submitted."
        )
    lines = (
        await session.scalars(select(StockCountLine).where(StockCountLine.count_id == count.id))
    ).all()
    uncounted = [line for line in lines if line.counted_quantity is None]
    if uncounted:
        raise InvalidCountStateError(
            f"{len(uncounted)} line(s) have not been counted yet. "
            "Every line needs a counted quantity before submitting."
        )

    count.status = "submitted"
    count.submitted_by = actor.id
    count.submitted_at = datetime.now(UTC)
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.stock_count.submitted",
        target_type="stock_count",
        target_id=count.id,
        request=request,
        safe_metadata={"count_number": count.count_number, "line_count": len(lines)},
    )
    return count


async def approve_count(
    session: AsyncSession, *, actor: StaffUser, count: StockCount, request: Request | None
) -> StockCount:
    if count.status != "submitted":
        raise InvalidCountStateError(
            f"Count {count.count_number} is {count.status}; only a submitted count can be approved."
        )

    location = await session.get(StorageLocation, count.storage_location_id)
    assert location is not None
    lines = (
        await session.scalars(select(StockCountLine).where(StockCountLine.count_id == count.id))
    ).all()

    corrections = 0
    for line in lines:
        if line.variance_quantity is None or line.variance_quantity == ZERO:
            continue
        item = await session.get(InventoryItem, line.inventory_item_id)
        assert item is not None
        batch = await session.get(InventoryBatch, line.batch_id) if line.batch_id else None

        movement = await ledger.post_movement(
            session,
            item=item,
            location=location,
            movement_type="stock_count_adjustment",
            quantity=abs(line.variance_quantity),
            batch=batch,
            actor_id=actor.id,
            occurred_at=datetime.now(UTC),
            reason=line.reason or f"Count {count.count_number} variance correction",
            reference_type="stock_count_line",
            reference_id=line.id,
            is_increase=line.variance_quantity > ZERO,
        )
        line.movement_id = movement.id
        corrections += 1

    count.status = "approved"
    count.approved_by = actor.id
    count.approved_at = datetime.now(UTC)
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.stock_count.approved",
        target_type="stock_count",
        target_id=count.id,
        request=request,
        safe_metadata={
            "count_number": count.count_number,
            "line_count": len(lines),
            "corrections_posted": corrections,
        },
    )
    await record_domain_event(
        session,
        event_type="inventory.stock_count.approved",
        aggregate_type="stock_count",
        aggregate_id=count.id,
        payload={"count_id": str(count.id), "count_number": count.count_number},
    )
    return count


async def cancel_count(
    session: AsyncSession, *, actor: StaffUser, count: StockCount, request: Request | None
) -> StockCount:
    if count.status not in ("draft", "in_progress", "submitted"):
        raise InvalidCountStateError(
            f"Count {count.count_number} is {count.status} and cannot be cancelled."
        )
    count.status = "cancelled"
    count.cancelled_at = datetime.now(UTC)
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.stock_count.cancelled",
        target_type="stock_count",
        target_id=count.id,
        request=request,
        safe_metadata={"count_number": count.count_number},
    )
    return count
