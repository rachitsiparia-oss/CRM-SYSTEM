"""Shared fixture-data builders for the Phase 8 inventory test suite.

Not a `test_*.py` module (pytest does not collect it), and not a fixture
module either — plain async helper functions, called directly from test
bodies with an explicit `db_session`, the same pattern `test_orders_api.py`
uses for its own `_make_product`/`_make_variant`. Inventory has enough
distinct reference-data entities (unit, category, location, supplier, item)
that duplicating these across six test files would violate CLAUDE.md
section 3's "avoid duplicating utilities" rule; a single shared module does
not.
"""

import uuid
from decimal import Decimal

from app.db.models import (
    InventoryBatch,
    InventoryCategory,
    InventoryItem,
    StorageLocation,
    Supplier,
    UnitOfMeasure,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def make_unit(
    session: AsyncSession,
    *,
    unit_type: str = "weight",
    base_unit_id: uuid.UUID | None = None,
    conversion_factor: Decimal = Decimal("1"),
    decimal_places: int = 3,
    **overrides: object,
) -> UnitOfMeasure:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": f"unit-{suffix}",
        "name": f"Unit {suffix}",
        "symbol": suffix[:6],
        "unit_type": unit_type,
        "base_unit_id": base_unit_id,
        "conversion_factor": conversion_factor,
        "decimal_places": decimal_places,
    }
    fields.update(overrides)
    unit = UnitOfMeasure(**fields)
    session.add(unit)
    await session.flush()
    return unit


async def make_weight_units(session: AsyncSession) -> tuple[UnitOfMeasure, UnitOfMeasure]:
    """A (gram, kilogram) pair with a real 1000x conversion factor."""
    gram = await make_unit(session, unit_type="weight", conversion_factor=Decimal("1"))
    kilogram = await make_unit(
        session, unit_type="weight", base_unit_id=gram.id, conversion_factor=Decimal("1000")
    )
    return gram, kilogram


async def make_category(session: AsyncSession, **overrides: object) -> InventoryCategory:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": f"cat-{suffix}",
        "name": f"Category {suffix}",
    }
    fields.update(overrides)
    category = InventoryCategory(**fields)
    session.add(category)
    await session.flush()
    return category


async def make_location(
    session: AsyncSession, *, allows_negative_stock: bool = False, **overrides: object
) -> StorageLocation:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": f"loc-{suffix}",
        "name": f"Location {suffix}",
        "location_type": "other",
        "allows_negative_stock": allows_negative_stock,
    }
    fields.update(overrides)
    location = StorageLocation(**fields)
    session.add(location)
    await session.flush()
    return location


async def make_supplier(session: AsyncSession, **overrides: object) -> Supplier:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "supplier_code": f"SUP-{suffix}",
        "name": f"Supplier {suffix}",
        "status": "active",
    }
    fields.update(overrides)
    supplier = Supplier(**fields)
    session.add(supplier)
    await session.flush()
    return supplier


async def make_item(
    session: AsyncSession,
    *,
    base_unit_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    reorder_level: Decimal = Decimal("10"),
    target_stock: Decimal = Decimal("50"),
    **overrides: object,
) -> InventoryItem:
    suffix = uuid.uuid4().hex[:10]
    if category_id is None:
        category_id = (await make_category(session)).id
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "item_code": f"ITM-{suffix}",
        "name": f"Item {suffix}",
        "category_id": category_id,
        "base_unit_id": base_unit_id,
        "reorder_level": reorder_level,
        "reorder_quantity": Decimal("20"),
        "target_stock": target_stock,
        "minimum_stock": Decimal("0"),
        "standard_cost_minor": 1000,
    }
    fields.update(overrides)
    item = InventoryItem(**fields)
    session.add(item)
    await session.flush()
    return item


async def make_batch(
    session: AsyncSession,
    *,
    item: InventoryItem,
    location: StorageLocation,
    received_quantity: Decimal,
    remaining_quantity: Decimal | None = None,
    **overrides: object,
) -> InventoryBatch:
    from datetime import UTC, datetime

    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "inventory_item_id": item.id,
        "batch_code": f"BATCH-{suffix}",
        "storage_location_id": location.id,
        "received_quantity": received_quantity,
        "remaining_quantity": (
            remaining_quantity if remaining_quantity is not None else received_quantity
        ),
        "received_at": datetime.now(UTC),
        "status": "active",
    }
    fields.update(overrides)
    batch = InventoryBatch(**fields)
    session.add(batch)
    await session.flush()
    return batch


async def make_stack(
    session: AsyncSession,
    *,
    requires_batch_tracking: bool = False,
    allows_negative_stock: bool = False,
    **item_overrides: object,
) -> tuple[InventoryItem, StorageLocation, UnitOfMeasure]:
    """The common case: one item with a piece-count base unit at one
    location, ready to post movements against."""
    unit = await make_unit(session, unit_type="count", decimal_places=0)
    location = await make_location(session, allows_negative_stock=allows_negative_stock)
    item = await make_item(
        session,
        base_unit_id=unit.id,
        requires_batch_tracking=requires_batch_tracking,
        requires_expiry_tracking=False,
        **item_overrides,
    )
    return item, location, unit
