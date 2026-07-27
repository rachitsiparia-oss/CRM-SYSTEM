"""Order-to-inventory integration — `app.inventory.order_integration`.

Covers this phase's explicit lifecycle: reserve on `confirmed`, consume on
`preparing` (replaying the exact reservation snapshot, not re-resolving),
release on cancellation before consumption, and the "never auto-restore
stock after consumption" rule — plus idempotency of every step.
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.db.models import (
    MenuCategory,
    Order,
    OrderItem,
    Product,
    StaffUser,
)
from app.inventory import ledger, order_integration
from app.inventory import recipes as recipes_service
from app.inventory.errors import InsufficientStockError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests._inventory_helpers import make_item, make_location, make_unit

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def _make_product(session: AsyncSession, *, price_minor: int = 10000) -> Product:
    suffix = uuid.uuid4().hex[:10]
    category = MenuCategory(id=uuid.uuid4(), code=f"cat-{suffix}", name="Test Category")
    session.add(category)
    await session.flush()
    product = Product(
        id=uuid.uuid4(),
        product_code=f"PROD-{suffix}",
        category_id=category.id,
        name=f"Product {suffix}",
        slug=f"product-{suffix}",
        food_type="vegetarian",
        base_price_minor=price_minor,
    )
    session.add(product)
    await session.flush()
    return product


async def _make_order(session: AsyncSession, *, product: Product, quantity: int = 1) -> Order:
    suffix = uuid.uuid4().hex[:10]
    order = Order(
        id=uuid.uuid4(),
        order_number=f"ORD-{suffix}",
        source="manual",
        order_type="takeaway",
        status="pending_confirmation",
        payment_status="pending",
    )
    session.add(order)
    await session.flush()
    session.add(
        OrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            quantity=quantity,
            unit_price_minor=product.base_price_minor,
            final_price_minor=product.base_price_minor * quantity,
            status="active",
        )
    )
    await session.flush()
    return order


async def _make_recipe_with_ingredient(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    ingredient_quantity: Decimal = Decimal("2"),
    item_reorder_level: Decimal = Decimal("0"),
    opening_stock: Decimal | None = Decimal("100"),
):
    unit = await make_unit(session, unit_type="count", decimal_places=0)
    location = await make_location(session)
    item = await make_item(
        session,
        base_unit_id=unit.id,
        default_location_id=location.id,
        reorder_level=item_reorder_level,
        standard_cost_minor=100,
    )
    if opening_stock is not None:
        await ledger.post_movement(
            session,
            item=item,
            location=location,
            movement_type="opening_balance",
            quantity=opening_stock,
            actor_id=actor.id,
        )

    recipe = await recipes_service.create_recipe(
        session,
        actor=actor,
        product_id=product.id,
        variant_id=None,
        yield_quantity=Decimal("1"),
        yield_unit_id=unit.id,
        preparation_loss_percentage=Decimal("0"),
        effective_from=datetime.now(UTC) - timedelta(hours=1),
        notes=None,
    )
    await recipes_service.add_recipe_item(
        session,
        recipe=recipe,
        inventory_item_id=item.id,
        quantity_required=ingredient_quantity,
        unit_id=unit.id,
        waste_factor=Decimal("0"),
        storage_location_id=None,
        display_order=0,
        notes=None,
    )
    return item, location, recipe


async def _balance(session: AsyncSession, item_id: uuid.UUID, location_id: uuid.UUID):
    from app.db.models import StockBalance

    return await session.scalar(
        select(StockBalance).where(
            StockBalance.inventory_item_id == item_id,
            StockBalance.storage_location_id == location_id,
            StockBalance.batch_id.is_(None),
        )
    )


# --- Reservation --------------------------------------------------------


async def test_reserve_product_without_recipe_is_skipped(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    order = await _make_order(db_session, product=product)

    state = await order_integration.reserve_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    assert state.state == "skipped"


async def test_reserve_with_recipe_creates_reservation_without_touching_on_hand(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    item, location, _recipe = await _make_recipe_with_ingredient(
        db_session, actor=actor, product=product, ingredient_quantity=Decimal("2")
    )
    order = await _make_order(db_session, product=product, quantity=3)

    state = await order_integration.reserve_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    assert state.state == "reserved"

    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("100.000")
    assert balance.reserved_quantity == Decimal("6.000")  # 2 per unit * 3 ordered


async def test_reserve_insufficient_stock_raises_and_leaves_state_pending(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    item, location, _recipe = await _make_recipe_with_ingredient(
        db_session,
        actor=actor,
        product=product,
        ingredient_quantity=Decimal("2"),
        opening_stock=Decimal("1"),  # not enough for 3 units * 2 each
    )
    order = await _make_order(db_session, product=product, quantity=3)

    with pytest.raises(InsufficientStockError):
        await order_integration.reserve_stock_for_order(
            db_session, actor=actor, order=order, request=None
        )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.reserved_quantity == Decimal("0.000")


async def test_reserve_is_idempotent(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    item, location, _recipe = await _make_recipe_with_ingredient(
        db_session, actor=actor, product=product, ingredient_quantity=Decimal("2")
    )
    order = await _make_order(db_session, product=product, quantity=3)

    await order_integration.reserve_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    await order_integration.reserve_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.reserved_quantity == Decimal("6.000")  # not doubled


# --- Consumption ----------------------------------------------------------


async def test_consume_deducts_on_hand_and_releases_reservation(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    item, location, _recipe = await _make_recipe_with_ingredient(
        db_session, actor=actor, product=product, ingredient_quantity=Decimal("2")
    )
    order = await _make_order(db_session, product=product, quantity=3)

    await order_integration.reserve_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    state = await order_integration.consume_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    assert state.state == "consumed"

    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("94.000")  # 100 - 6
    assert balance.reserved_quantity == Decimal("0.000")


async def test_consume_is_idempotent(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    item, location, _recipe = await _make_recipe_with_ingredient(
        db_session, actor=actor, product=product, ingredient_quantity=Decimal("2")
    )
    order = await _make_order(db_session, product=product, quantity=3)

    await order_integration.reserve_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    await order_integration.consume_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    await order_integration.consume_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("94.000")  # not double-deducted


async def test_consume_without_prior_reservation_is_skipped(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    _item, _location, _recipe = await _make_recipe_with_ingredient(
        db_session, actor=actor, product=product
    )
    order = await _make_order(db_session, product=product, quantity=1)

    state = await order_integration.consume_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    assert state.state == "skipped"


# --- Release / cancellation ------------------------------------------------


async def test_release_before_consumption_restores_reservation_without_stock_change(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    item, location, _recipe = await _make_recipe_with_ingredient(
        db_session, actor=actor, product=product, ingredient_quantity=Decimal("2")
    )
    order = await _make_order(db_session, product=product, quantity=3)

    await order_integration.reserve_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    state = await order_integration.release_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    assert state.state == "released"

    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("100.000")  # unchanged
    assert balance.reserved_quantity == Decimal("0.000")


async def test_release_after_consumption_does_not_restore_stock(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    item, location, _recipe = await _make_recipe_with_ingredient(
        db_session, actor=actor, product=product, ingredient_quantity=Decimal("2")
    )
    order = await _make_order(db_session, product=product, quantity=3)

    await order_integration.reserve_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    await order_integration.consume_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    state = await order_integration.release_stock_for_order(
        db_session, actor=actor, order=order, request=None
    )
    assert state.state == "consumed"  # unchanged — not silently reverted to released
    assert state.post_consumption_note is not None

    balance = await _balance(db_session, item.id, location.id)
    assert balance.on_hand_quantity == Decimal("94.000")  # NOT restored to 100
