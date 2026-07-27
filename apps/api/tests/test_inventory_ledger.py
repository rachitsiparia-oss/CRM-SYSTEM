"""The append-only stock ledger and balance projection —
`app.inventory.ledger` and `app.inventory.balances`.

Covers this phase's non-negotiable invariants: the ledger is the sole
source of truth, repeated requests never double-deduct or double-add stock,
negative stock is refused unless the location explicitly allows it, and
drift between the ledger and its projection is detected rather than
silently healed.
"""

import uuid
from collections.abc import Awaitable, Callable
from decimal import Decimal

import pytest
from app.db.models import StaffUser
from app.inventory import balances as balances_service
from app.inventory import ledger
from app.inventory.errors import (
    DuplicateIdempotencyKeyError,
    InsufficientStockError,
    NegativeStockNotAllowedError,
    ReservationMismatchError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests._inventory_helpers import make_batch, make_stack

pytestmark = pytest.mark.asyncio

ZERO = Decimal("0.000")
MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def _balance(session: AsyncSession, item_id: uuid.UUID, location_id: uuid.UUID):
    from app.db.models import StockBalance

    return await session.scalar(
        select(StockBalance).where(
            StockBalance.inventory_item_id == item_id,
            StockBalance.storage_location_id == location_id,
            StockBalance.batch_id.is_(None),
        )
    )


# --- Sign convention and rollups --------------------------------------------


async def test_opening_balance_increases_on_hand(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("10.000")
    await db_session.refresh(item)
    assert item.current_stock == Decimal("10.000")


async def test_wastage_decreases_on_hand(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="wastage",
        quantity=Decimal("3"),
        actor_id=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("7.000")


async def test_post_movement_rejects_non_positive_quantity(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    with pytest.raises(ValueError):
        await ledger.post_movement(
            db_session,
            item=item,
            location=location,
            movement_type="opening_balance",
            quantity=Decimal("0"),
            actor_id=None,
        )


async def test_post_movement_rejects_unknown_type(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    with pytest.raises(ValueError):
        await ledger.post_movement(
            db_session,
            item=item,
            location=location,
            movement_type="teleportation",
            quantity=Decimal("1"),
            actor_id=None,
        )


async def test_stock_count_adjustment_requires_is_increase(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    with pytest.raises(ValueError):
        await ledger.post_movement(
            db_session,
            item=item,
            location=location,
            movement_type="stock_count_adjustment",
            quantity=Decimal("1"),
            actor_id=None,
        )


async def test_stock_count_adjustment_can_increase_or_decrease(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="stock_count_adjustment",
        quantity=Decimal("2"),
        actor_id=None,
        is_increase=False,
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("8.000")


# --- Negative stock prevention -----------------------------------------------


async def test_negative_stock_rejected_by_default(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    with pytest.raises(NegativeStockNotAllowedError):
        await ledger.post_movement(
            db_session,
            item=item,
            location=location,
            movement_type="wastage",
            quantity=Decimal("1"),
            actor_id=None,
        )


async def test_negative_stock_allowed_when_location_permits(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session, allows_negative_stock=True)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="wastage",
        quantity=Decimal("1"),
        actor_id=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("-1.000")


# --- Idempotency --------------------------------------------------------------


async def test_duplicate_idempotency_key_rejected(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    key = f"idem-{uuid.uuid4().hex}"
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("5"),
        actor_id=None,
        idempotency_key=key,
    )
    with pytest.raises(DuplicateIdempotencyKeyError):
        await ledger.post_movement(
            db_session,
            item=item,
            location=location,
            movement_type="opening_balance",
            quantity=Decimal("5"),
            actor_id=None,
            idempotency_key=key,
        )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("5.000")  # not doubled


async def test_find_by_idempotency_key_enables_caller_side_no_op(
    db_session: AsyncSession,
) -> None:
    """The pattern every seed/service caller actually uses: check first,
    skip if already posted, rather than relying on the exception."""
    item, location, _unit = await make_stack(db_session)
    key = f"idem-{uuid.uuid4().hex}"
    assert await ledger.find_by_idempotency_key(db_session, key) is None
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("5"),
        actor_id=None,
        idempotency_key=key,
    )
    assert await ledger.find_by_idempotency_key(db_session, key) is not None


# --- Reservations ---------------------------------------------------------


async def test_reservation_moves_quantity_without_touching_on_hand(
    db_session: AsyncSession,
) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="order_reservation",
        quantity=Decimal("4"),
        actor_id=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("10.000")
    assert balance.reserved_quantity == Decimal("4.000")
    available = await ledger.available_quantity(
        db_session, inventory_item_id=item.id, storage_location_id=location.id
    )
    assert available == Decimal("6.000")


async def test_reservation_exceeding_available_raises(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("3"),
        actor_id=None,
    )
    with pytest.raises(InsufficientStockError):
        await ledger.post_movement(
            db_session,
            item=item,
            location=location,
            movement_type="order_reservation",
            quantity=Decimal("5"),
            actor_id=None,
        )


async def test_reservation_release_returns_quantity(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="order_reservation",
        quantity=Decimal("4"),
        actor_id=None,
    )
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="reservation_release",
        quantity=Decimal("4"),
        actor_id=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.reserved_quantity == ZERO


async def test_release_exceeding_reserved_raises(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="order_reservation",
        quantity=Decimal("2"),
        actor_id=None,
    )
    with pytest.raises(ReservationMismatchError):
        await ledger.post_movement(
            db_session,
            item=item,
            location=location,
            movement_type="reservation_release",
            quantity=Decimal("5"),
            actor_id=None,
        )


# --- Reversal ------------------------------------------------------------


async def test_reverse_movement_undoes_on_hand_effect(db_session: AsyncSession) -> None:
    item, location, _unit = await make_stack(db_session)
    original = await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    await ledger.reverse_movement(
        db_session, original=original, item=item, location=location, actor_id=None, reason="test"
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == ZERO
    await db_session.refresh(original)
    assert original.reversed_by_movement_id is not None
    assert original.reversed_at is not None


async def test_reverse_movement_twice_raises(db_session: AsyncSession) -> None:
    from app.inventory.errors import AlreadyReversedError

    item, location, _unit = await make_stack(db_session)
    original = await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    await ledger.reverse_movement(
        db_session, original=original, item=item, location=location, actor_id=None, reason="test"
    )
    with pytest.raises(AlreadyReversedError):
        await ledger.reverse_movement(
            db_session,
            original=original,
            item=item,
            location=location,
            actor_id=None,
            reason="test again",
        )


# --- Batch remaining_quantity tracking (regression: double-count bug) -----


async def test_posting_against_a_freshly_created_batch_sets_remaining_exactly_once(
    db_session: AsyncSession,
) -> None:
    """Regression test: a batch created with `remaining_quantity` pre-set
    to the posted amount, followed by `post_movement`'s own increment,
    silently doubled the batch's remaining stock. The correct pattern is a
    batch created at zero, with the ledger post as its sole writer."""
    item, location, _unit = await make_stack(db_session, requires_batch_tracking=True)
    batch = await make_batch(
        db_session,
        item=item,
        location=location,
        received_quantity=Decimal("20"),
        remaining_quantity=ZERO,
    )
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="purchase_receipt",
        quantity=Decimal("20"),
        batch=batch,
        actor_id=None,
    )
    await db_session.refresh(batch)
    assert batch.remaining_quantity == Decimal("20.000")


# --- Balance drift detection and rebuild ------------------------------------


async def test_verify_balances_detects_no_drift_after_normal_posting(
    db_session: AsyncSession,
) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    drifts = await balances_service.verify_balances(db_session, inventory_item_id=item.id)
    assert drifts == []


async def test_verify_balances_detects_manually_corrupted_projection(
    db_session: AsyncSession,
) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    balance.on_hand_quantity = Decimal("999.000")  # corrupt the projection directly
    await db_session.flush()

    drifts = await balances_service.verify_balances(db_session, inventory_item_id=item.id)
    assert len(drifts) == 1
    assert drifts[0].projected_on_hand == Decimal("999.000")
    assert drifts[0].ledger_on_hand == Decimal("10.000")

    # verify_balances must not have healed anything.
    await db_session.refresh(balance)
    assert balance.on_hand_quantity == Decimal("999.000")


async def test_rebuild_balances_corrects_drift(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    item, location, _unit = await make_stack(db_session)
    await ledger.post_movement(
        db_session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=Decimal("10"),
        actor_id=None,
    )
    balance = await _balance(db_session, item.id, location.id)
    balance.on_hand_quantity = Decimal("999.000")
    await db_session.flush()

    actor = await make_staff_user(role_code="owner")
    await balances_service.rebuild_balances(db_session, actor=actor, inventory_item_id=item.id)

    await db_session.refresh(balance)
    assert balance.on_hand_quantity == Decimal("10.000")
    drifts = await balances_service.verify_balances(db_session, inventory_item_id=item.id)
    assert drifts == []
