"""Idempotent development seed data for Phase 8 inventory —
PROJECT_PLAN.md section 8 (dummy inventory master, section 8.2's dummy
stock catalogue) and section 9 (dummy supplier directory).

Reuses `app.inventory`'s actual service functions (`ledger.post_movement`,
`receipts.*`, `adjustments.*`, `wastage.*`, `transfers.*`, `stock_counts.*`,
`recipes.*`) rather than constructing ledger rows by hand — the same
precedent `app.orders.seed` and `app.menu.seed` already set — so seed data
exercises the exact same validation, audit, and outbox logic real API calls
do, and doubles as a smoke test of the service layer.

**Supplier deviation** (recorded in DATABASE_AND_API.md section 9.8):
PROJECT_PLAN.md section 9 documents exactly eight suppliers in full. Several
catalogue rows in section 8.2 name a supplier outside that list ("In-house
production", "GreenGrain Foods", "FreshForm Foods", "Metro Grain Traders",
"Metro Oil Traders", "Beverage Partner Demo", "ClearSpring Beverages",
"SweetLine Desserts"). Rather than fabricating supplier records the
canonical directory does not define, `preferred_supplier_id` is left unset
for those items — `_SUPPLIER_DEFS` only carries the eight suppliers that
appear in section 9, so `suppliers.get(name)` returns `None` for the rest.

**Idempotency**: every mutation the ledger would otherwise reject on a
rerun (a duplicate opening balance, a second identical receipt, a second
identical adjustment) is guarded by checking for its effect first — a fixed
`idempotency_key` for single ledger movements, and a fixed marker in
`supplier_reference`/`notes` for multi-step documents (receipts, transfers,
counts) where the service layer itself does not expose one. Running
`seed_inventory` twice must leave every quantity, balance, and row count
unchanged.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    InventoryCategory,
    InventoryItem,
    Product,
    ProductVariant,
    StaffUser,
    StockCount,
    StockCountLine,
    StockReceipt,
    StockTransfer,
    StorageLocation,
    Supplier,
    UnitOfMeasure,
)
from app.inventory import adjustments as adjustments_service
from app.inventory import ledger
from app.inventory import receipts as receipts_service
from app.inventory import recipes as recipes_service
from app.inventory import stock_counts as stock_counts_service
from app.inventory import transfers as transfers_service
from app.inventory import wastage as wastage_service
from app.inventory.items import generate_item_code

ZERO = Decimal("0.000")
_SEED_RECEIPT_MARKER = "SEED-RECEIPT-DAIRY-001"
_SEED_TRANSFER_MARKER = "SEED-TRANSFER-COOKING-OIL-001"
_SEED_COUNT_MARKER = "SEED-COUNT-BAR-001"


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    stmt = select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    result = await session.scalar(stmt)
    return result


# --- Reference data -----------------------------------------------------


async def _get_or_create_unit(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    symbol: str,
    unit_type: str,
    base_unit_id: uuid.UUID | None,
    conversion_factor: Decimal,
    decimal_places: int,
    sort_order: int,
    actor: StaffUser | None,
) -> UnitOfMeasure:
    existing = await session.scalar(select(UnitOfMeasure).where(UnitOfMeasure.code == code))
    if existing is not None:
        return existing
    unit = UnitOfMeasure(
        id=uuid.uuid4(),
        code=code,
        name=name,
        symbol=symbol,
        unit_type=unit_type,
        base_unit_id=base_unit_id,
        conversion_factor=conversion_factor,
        decimal_places=decimal_places,
        sort_order=sort_order,
        created_by=actor.id if actor else None,
    )
    session.add(unit)
    await session.flush()
    return unit


async def _get_or_create_category(
    session: AsyncSession, *, code: str, name: str, sort_order: int, actor: StaffUser | None
) -> InventoryCategory:
    existing = await session.scalar(select(InventoryCategory).where(InventoryCategory.code == code))
    if existing is not None:
        return existing
    category = InventoryCategory(
        id=uuid.uuid4(),
        code=code,
        name=name,
        sort_order=sort_order,
        created_by=actor.id if actor else None,
    )
    session.add(category)
    await session.flush()
    return category


async def _get_or_create_location(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    location_type: str,
    sort_order: int,
    actor: StaffUser | None,
) -> StorageLocation:
    existing = await session.scalar(select(StorageLocation).where(StorageLocation.code == code))
    if existing is not None:
        return existing
    location = StorageLocation(
        id=uuid.uuid4(),
        code=code,
        name=name,
        location_type=location_type,
        sort_order=sort_order,
        created_by=actor.id if actor else None,
    )
    session.add(location)
    await session.flush()
    return location


async def _get_or_create_supplier(
    session: AsyncSession,
    *,
    supplier_code: str,
    name: str,
    contact_person: str,
    phone_e164: str,
    email: str,
    address_line1: str,
    city: str,
    state: str,
    postal_code: str,
    supply_categories: list[str],
    normal_lead_time_days: int | None,
    payment_terms: str,
    minimum_order_value_minor: int,
    actor: StaffUser | None,
) -> Supplier:
    existing = await session.scalar(select(Supplier).where(Supplier.supplier_code == supplier_code))
    if existing is not None:
        return existing
    supplier = Supplier(
        id=uuid.uuid4(),
        supplier_code=supplier_code,
        name=name,
        contact_person=contact_person,
        phone_e164=phone_e164,
        email=email,
        address_line1=address_line1,
        city=city,
        state=state,
        postal_code=postal_code,
        country="IN",
        supply_categories=supply_categories,
        normal_lead_time_days=normal_lead_time_days,
        payment_terms=payment_terms,
        minimum_order_value_minor=minimum_order_value_minor,
        status="active",
        created_by=actor.id if actor else None,
    )
    session.add(supplier)
    await session.flush()
    return supplier


async def _get_or_create_item(
    session: AsyncSession, *, name: str, actor: StaffUser | None, **fields: object
) -> tuple[InventoryItem, bool]:
    existing = await session.scalar(select(InventoryItem).where(InventoryItem.name == name))
    if existing is not None:
        return existing, False
    item = InventoryItem(
        id=uuid.uuid4(),
        item_code=generate_item_code(),
        name=name,
        created_by=actor.id if actor else None,
        **fields,
    )
    session.add(item)
    await session.flush()
    return item, True


async def _seed_opening_balance(
    session: AsyncSession,
    *,
    item: InventoryItem,
    location: StorageLocation,
    quantity: Decimal,
    actor: StaffUser | None,
) -> None:
    if quantity <= ZERO:
        return
    idempotency_key = f"seed-opening-balance-{item.item_code}"
    if await ledger.find_by_idempotency_key(session, idempotency_key) is not None:
        return
    await ledger.post_movement(
        session,
        item=item,
        location=location,
        movement_type="opening_balance",
        quantity=quantity,
        actor_id=actor.id if actor else None,
        reason="Seed data: opening balance",
        reference_type="seed_data",
        idempotency_key=idempotency_key,
    )


def _minor(rupees: int) -> int:
    return rupees * 100


# --- Units of measure — this phase's own example list, verbatim ---------

_UNIT_DEFS: tuple[tuple[str, str, str, str, str | None, Decimal, int, int], ...] = (
    # code,     name,        symbol, type,    base_code, factor,          decimals, sort
    ("gram", "Gram", "g", "weight", None, Decimal("1"), 0, 0),
    ("kilogram", "Kilogram", "kg", "weight", "gram", Decimal("1000"), 3, 1),
    ("millilitre", "Millilitre", "ml", "volume", None, Decimal("1"), 0, 0),
    ("litre", "Litre", "L", "volume", "millilitre", Decimal("1000"), 3, 1),
    ("piece", "Piece", "pc", "count", None, Decimal("1"), 0, 0),
    ("packet", "Packet", "pkt", "count", "piece", Decimal("1"), 0, 1),
    ("box", "Box", "box", "count", "piece", Decimal("1"), 0, 2),
    ("bottle", "Bottle", "btl", "count", "piece", Decimal("1"), 0, 3),
    ("tray", "Tray", "tray", "count", "piece", Decimal("1"), 0, 4),
)

_CATEGORY_DEFS: tuple[tuple[str, str], ...] = (
    ("bakery", "Bakery"),
    ("proteins", "Proteins"),
    ("dairy", "Dairy"),
    ("produce", "Produce"),
    ("pantry", "Pantry and Dry Goods"),
    ("sauces", "Sauces and Condiments"),
    ("beverages", "Beverages"),
    ("desserts", "Desserts and Frozen"),
    ("packaging", "Packaging and Disposables"),
)

_LOCATION_DEFS: tuple[tuple[str, str, str], ...] = (
    ("main-kitchen", "Main Kitchen", "kitchen"),
    ("dry-store", "Dry Store", "dry_store"),
    ("cold-storage", "Cold Storage", "chilled"),
    ("freezer", "Freezer", "frozen"),
    ("bar", "Bar", "bar"),
    ("packaging-store", "Packaging Store", "packaging"),
)

# PROJECT_PLAN.md section 9 — the eight canonical suppliers, verbatim.
_SUPPLIER_DEFS: tuple[
    tuple[str, str, str, str, str, str, str, str, list[str], int | None, str, int], ...
] = (
    (
        "SUP-BAK-001",
        "Bengaluru Bakers Supply",
        "Harish Verma",
        "+91 98860 11001",
        "orders@bengaluru-bakers-demo.example",
        "41, Industrial Bakery Lane, Peenya",
        "Bengaluru",
        "560058",
        ["Burger buns", "brownies", "garlic bread"],
        1,
        "15 days",
        500000,
    ),
    (
        "SUP-DAI-002",
        "Nandi Dairy Foods",
        "Divya Rao",
        "+91 98860 11002",
        "sales@nandi-dairy-demo.example",
        "12, Dairy Market Road, Yeshwanthpur",
        "Bengaluru",
        "560022",
        ["Mozzarella", "cheddar", "paneer", "ice cream"],
        1,
        "15 days",
        750000,
    ),
    (
        "SUP-POU-003",
        "Southern Poultry Co.",
        "Imran Ali",
        "+91 98860 11003",
        "dispatch@southern-poultry-demo.example",
        "27, Cold Chain Park, Nelamangala",
        "Bengaluru Rural",
        "562123",
        ["Chicken patties", "chicken fillets", "boneless chicken"],
        2,
        "7 days",
        1000000,
    ),
    (
        "SUP-VEG-004",
        "GreenLeaf Produce",
        "Lakshmi Narayan",
        "+91 98860 11004",
        "supply@greenleaf-produce-demo.example",
        "Stall 118, APMC Yard, Yeshwanthpur",
        "Bengaluru",
        "560022",
        ["Lettuce", "tomato", "onion", "capsicum", "mushroom", "herbs"],
        0,
        "Weekly settlement",
        200000,
    ),
    (
        "SUP-FRO-005",
        "FrostBite Distributors",
        "Akash Mehta",
        "+91 98860 11005",
        "orders@frostbite-demo.example",
        "Unit 8, Cold Storage Estate, Hoskote",
        "Bengaluru Rural",
        "562114",
        ["Fries", "onion rings", "corn", "frozen products"],
        2,
        "15 days",
        800000,
    ),
    (
        "SUP-MEX-006",
        "MexiSource India",
        "Maria D'Souza",
        "+91 98860 11006",
        "sales@mexisource-demo.example",
        "63, Food Import Hub, Whitefield",
        "Bengaluru",
        "560066",
        ["Taco shells", "tortillas", "jalapenos", "Mexican ingredients"],
        3,
        "Advance for imported items",
        1200000,
    ),
    (
        "SUP-CON-007",
        "TasteCraft Condiments",
        "Rohit Bansal",
        "+91 98860 11007",
        "b2b@tastecraft-demo.example",
        "14, Food Processing Cluster, Bommasandra",
        "Bengaluru",
        "560099",
        ["Sauces", "pickles", "condiments"],
        3,
        "15 days",
        600000,
    ),
    (
        "SUP-PAC-008",
        "EcoPack Bengaluru",
        "Asha Menon",
        "+91 98860 11008",
        "orders@ecopack-demo.example",
        "77, Packaging Industrial Area, Kumbalgodu",
        "Bengaluru",
        "560074",
        ["Boxes", "bags", "napkins", "cups", "cutlery"],
        4,
        "30 days",
        1500000,
    ),
)

# PROJECT_PLAN.md section 8.2's dummy stock catalogue.
# name, category_code, unit_code, current, reorder, target, cost_rupees,
# supplier_name (or None if not in section 9), location_code, shelf_life_days,
# is_perishable
_ITEM_DEFS: tuple[
    tuple[str, str, str, Decimal, Decimal, Decimal, int, str | None, str, int | None, bool], ...
] = (
    (
        "Burger buns",
        "bakery",
        "piece",
        Decimal("420"),
        Decimal("120"),
        Decimal("500"),
        18,
        "Bengaluru Bakers Supply",
        "dry-store",
        4,
        True,
    ),
    (
        "Gluten-aware buns",
        "bakery",
        "piece",
        Decimal("35"),
        Decimal("10"),
        Decimal("40"),
        42,
        None,
        "dry-store",
        5,
        True,
    ),
    (
        "Vegetable burger patties",
        "proteins",
        "piece",
        Decimal("210"),
        Decimal("60"),
        Decimal("250"),
        34,
        None,
        "freezer",
        60,
        True,
    ),
    (
        "Chicken burger patties",
        "proteins",
        "piece",
        Decimal("180"),
        Decimal("50"),
        Decimal("220"),
        72,
        "Southern Poultry Co.",
        "freezer",
        45,
        True,
    ),
    (
        "Crispy chicken fillets",
        "proteins",
        "piece",
        Decimal("160"),
        Decimal("45"),
        Decimal("200"),
        78,
        "Southern Poultry Co.",
        "freezer",
        None,
        True,
    ),
    (
        "Pizza dough balls, small",
        "bakery",
        "piece",
        Decimal("130"),
        Decimal("40"),
        Decimal("170"),
        24,
        None,
        "main-kitchen",
        None,
        True,
    ),
    (
        "Pizza dough balls, large",
        "bakery",
        "piece",
        Decimal("95"),
        Decimal("30"),
        Decimal("130"),
        38,
        None,
        "main-kitchen",
        None,
        True,
    ),
    (
        "Paneer",
        "dairy",
        "kilogram",
        Decimal("29"),
        Decimal("8"),
        Decimal("35"),
        390,
        "Nandi Dairy Foods",
        "cold-storage",
        None,
        True,
    ),
    (
        "Boneless chicken",
        "proteins",
        "kilogram",
        Decimal("34"),
        Decimal("10"),
        Decimal("42"),
        310,
        "Southern Poultry Co.",
        "freezer",
        None,
        True,
    ),
    (
        "French fries, frozen",
        "pantry",
        "kilogram",
        Decimal("62"),
        Decimal("18"),
        Decimal("75"),
        155,
        "FrostBite Distributors",
        "freezer",
        None,
        False,
    ),
    (
        "Onion rings, frozen",
        "pantry",
        "kilogram",
        Decimal("14"),
        Decimal("5"),
        Decimal("18"),
        220,
        "FrostBite Distributors",
        "freezer",
        None,
        False,
    ),
    (
        "Taco shells",
        "pantry",
        "piece",
        Decimal("360"),
        Decimal("100"),
        Decimal("450"),
        12,
        "MexiSource India",
        "dry-store",
        None,
        False,
    ),
    (
        "Large tortillas",
        "pantry",
        "piece",
        Decimal("240"),
        Decimal("70"),
        Decimal("300"),
        17,
        "MexiSource India",
        "dry-store",
        None,
        False,
    ),
    (
        "Mexican rice",
        "pantry",
        "kilogram",
        Decimal("28"),
        Decimal("8"),
        Decimal("35"),
        92,
        None,
        "dry-store",
        None,
        False,
    ),
    (
        "Black beans",
        "pantry",
        "kilogram",
        Decimal("18"),
        Decimal("5"),
        Decimal("22"),
        145,
        None,
        "dry-store",
        None,
        False,
    ),
    (
        "Lettuce",
        "produce",
        "kilogram",
        Decimal("17"),
        Decimal("5"),
        Decimal("22"),
        105,
        "GreenLeaf Produce",
        "cold-storage",
        5,
        True,
    ),
    (
        "Tomatoes",
        "produce",
        "kilogram",
        Decimal("24"),
        Decimal("7"),
        Decimal("30"),
        42,
        "GreenLeaf Produce",
        "cold-storage",
        6,
        True,
    ),
    (
        "Onions",
        "produce",
        "kilogram",
        Decimal("30"),
        Decimal("8"),
        Decimal("38"),
        38,
        "GreenLeaf Produce",
        "cold-storage",
        14,
        True,
    ),
    (
        "Capsicum",
        "produce",
        "kilogram",
        Decimal("12"),
        Decimal("4"),
        Decimal("16"),
        84,
        "GreenLeaf Produce",
        "cold-storage",
        7,
        True,
    ),
    (
        "Mushrooms",
        "produce",
        "kilogram",
        Decimal("8"),
        Decimal("3"),
        Decimal("10"),
        190,
        "GreenLeaf Produce",
        "cold-storage",
        5,
        True,
    ),
    (
        "Sweet corn",
        "produce",
        "kilogram",
        Decimal("15"),
        Decimal("4"),
        Decimal("18"),
        120,
        "FrostBite Distributors",
        "freezer",
        None,
        True,
    ),
    (
        "Jalapenos",
        "produce",
        "kilogram",
        Decimal("7"),
        Decimal("2"),
        Decimal("9"),
        280,
        "MexiSource India",
        "cold-storage",
        None,
        True,
    ),
    (
        "Pickles",
        "sauces",
        "kilogram",
        Decimal("10"),
        Decimal("3"),
        Decimal("12"),
        160,
        "TasteCraft Condiments",
        "dry-store",
        None,
        False,
    ),
    (
        "Burger sauce",
        "sauces",
        "litre",
        Decimal("18"),
        Decimal("5"),
        Decimal("22"),
        210,
        None,
        "main-kitchen",
        None,
        True,
    ),
    (
        "Chipotle sauce",
        "sauces",
        "litre",
        Decimal("12"),
        Decimal("4"),
        Decimal("15"),
        260,
        "TasteCraft Condiments",
        "dry-store",
        None,
        True,
    ),
    (
        "Barbecue sauce",
        "sauces",
        "litre",
        Decimal("11"),
        Decimal("3"),
        Decimal("14"),
        230,
        "TasteCraft Condiments",
        "dry-store",
        None,
        True,
    ),
    (
        "Tomato pizza sauce",
        "sauces",
        "litre",
        Decimal("21"),
        Decimal("6"),
        Decimal("26"),
        175,
        None,
        "main-kitchen",
        None,
        True,
    ),
    (
        "Cooking oil",
        "pantry",
        "litre",
        Decimal("95"),
        Decimal("25"),
        Decimal("120"),
        128,
        None,
        "dry-store",
        None,
        False,
    ),
    (
        "Cola syrup",
        "beverages",
        "litre",
        Decimal("20"),
        Decimal("6"),
        Decimal("25"),
        145,
        None,
        "bar",
        None,
        False,
    ),
    (
        "Mineral water bottles",
        "beverages",
        "bottle",
        Decimal("420"),
        Decimal("120"),
        Decimal("500"),
        16,
        None,
        "bar",
        None,
        False,
    ),
    (
        "Brownies",
        "desserts",
        "piece",
        Decimal("80"),
        Decimal("25"),
        Decimal("100"),
        62,
        "Bengaluru Bakers Supply",
        "cold-storage",
        3,
        True,
    ),
    (
        "Cheesecake slices",
        "desserts",
        "piece",
        Decimal("42"),
        Decimal("12"),
        Decimal("50"),
        98,
        None,
        "cold-storage",
        3,
        True,
    ),
    (
        "Vanilla ice cream",
        "desserts",
        "litre",
        Decimal("16"),
        Decimal("5"),
        Decimal("20"),
        240,
        "Nandi Dairy Foods",
        "freezer",
        None,
        True,
    ),
    (
        "Paper burger boxes",
        "packaging",
        "piece",
        Decimal("900"),
        Decimal("250"),
        Decimal("1200"),
        7,
        "EcoPack Bengaluru",
        "packaging-store",
        None,
        False,
    ),
    (
        "Pizza boxes, small",
        "packaging",
        "piece",
        Decimal("320"),
        Decimal("100"),
        Decimal("400"),
        11,
        "EcoPack Bengaluru",
        "packaging-store",
        None,
        False,
    ),
    (
        "Pizza boxes, large",
        "packaging",
        "piece",
        Decimal("270"),
        Decimal("80"),
        Decimal("350"),
        16,
        "EcoPack Bengaluru",
        "packaging-store",
        None,
        False,
    ),
    (
        "Takeaway bags",
        "packaging",
        "piece",
        Decimal("540"),
        Decimal("150"),
        Decimal("700"),
        8,
        "EcoPack Bengaluru",
        "packaging-store",
        None,
        False,
    ),
    (
        "Napkin packs",
        "packaging",
        "packet",
        Decimal("310"),
        Decimal("80"),
        Decimal("400"),
        12,
        "EcoPack Bengaluru",
        "packaging-store",
        None,
        False,
    ),
)

# The three items whose entire opening stock arrives through the one seeded
# purchase receipt instead of a standalone opening-balance movement — see
# `_seed_receipt`. Mozzarella cheese and Cheddar slices are not in
# `_ITEM_DEFS` above (they are batch/receipt-only additions); Cheddar
# slices is plain stock, Mozzarella cheese is this phase's expiring-batch
# example, Paneer burger patties is its second batch-tracked example.
_RECEIPT_ITEM_NAMES = ("Mozzarella cheese", "Cheddar slices", "Paneer burger patties")


async def _seed_units(
    session: AsyncSession, *, actor: StaffUser | None
) -> dict[str, UnitOfMeasure]:
    units: dict[str, UnitOfMeasure] = {}
    for code, name, symbol, unit_type, base_code, factor, decimals, sort_order in _UNIT_DEFS:
        base_unit_id = units[base_code].id if base_code else None
        units[code] = await _get_or_create_unit(
            session,
            code=code,
            name=name,
            symbol=symbol,
            unit_type=unit_type,
            base_unit_id=base_unit_id,
            conversion_factor=factor,
            decimal_places=decimals,
            sort_order=sort_order,
            actor=actor,
        )
    return units


async def _seed_categories(
    session: AsyncSession, *, actor: StaffUser | None
) -> dict[str, InventoryCategory]:
    return {
        code: await _get_or_create_category(
            session, code=code, name=name, sort_order=i, actor=actor
        )
        for i, (code, name) in enumerate(_CATEGORY_DEFS)
    }


async def _seed_locations(
    session: AsyncSession, *, actor: StaffUser | None
) -> dict[str, StorageLocation]:
    return {
        code: await _get_or_create_location(
            session, code=code, name=name, location_type=loc_type, sort_order=i, actor=actor
        )
        for i, (code, name, loc_type) in enumerate(_LOCATION_DEFS)
    }


async def _seed_suppliers(session: AsyncSession, *, actor: StaffUser | None) -> dict[str, Supplier]:
    suppliers: dict[str, Supplier] = {}
    for (
        code,
        name,
        contact,
        phone,
        email,
        address,
        city,
        postal,
        categories,
        lead_time,
        terms,
        min_order,
    ) in _SUPPLIER_DEFS:
        suppliers[name] = await _get_or_create_supplier(
            session,
            supplier_code=code,
            name=name,
            contact_person=contact,
            phone_e164=phone,
            email=email,
            address_line1=address,
            city=city,
            state="Karnataka",
            postal_code=postal,
            supply_categories=categories,
            normal_lead_time_days=lead_time,
            payment_terms=terms,
            minimum_order_value_minor=min_order,
            actor=actor,
        )
    return suppliers


async def _seed_items(
    session: AsyncSession,
    *,
    units: dict[str, UnitOfMeasure],
    categories: dict[str, InventoryCategory],
    locations: dict[str, StorageLocation],
    suppliers: dict[str, Supplier],
    actor: StaffUser | None,
) -> dict[str, InventoryItem]:
    items: dict[str, InventoryItem] = {}

    for (
        name,
        category_code,
        unit_code,
        current,
        reorder,
        target,
        cost_rupees,
        supplier_name,
        location_code,
        shelf_life_days,
        is_perishable,
    ) in _ITEM_DEFS:
        unit = units[unit_code]
        location = locations[location_code]
        supplier = suppliers.get(supplier_name) if supplier_name else None
        purchase_unit_id = unit.id
        purchase_conversion_factor: Decimal | None = None
        if name == "Burger buns":
            # Demonstrates the packaging-unit purchase-conversion case
            # (units.py's `convert_purchase_quantity`): bought by the
            # packet of 20, stocked in pieces.
            purchase_unit_id = units["packet"].id
            purchase_conversion_factor = Decimal("20")

        reorder_quantity = target - reorder if target > reorder else reorder
        item, created = await _get_or_create_item(
            session,
            name=name,
            actor=actor,
            category_id=categories[category_code].id,
            base_unit_id=unit.id,
            default_purchase_unit_id=purchase_unit_id,
            purchase_conversion_factor=purchase_conversion_factor,
            default_location_id=location.id,
            preferred_supplier_id=supplier.id if supplier else None,
            reorder_level=reorder,
            reorder_quantity=reorder_quantity,
            target_stock=target,
            minimum_stock=Decimal("0.000"),
            standard_cost_minor=_minor(cost_rupees),
            lead_time_days=supplier.normal_lead_time_days if supplier else None,
            shelf_life_days=shelf_life_days,
            is_perishable=is_perishable,
            requires_batch_tracking=False,
            requires_expiry_tracking=False,
        )
        items[name] = item
        if created:
            await _seed_opening_balance(
                session, item=item, location=location, quantity=current, actor=actor
            )

    # --- The two batch/expiry-tracked items, seeded via the one purchase
    # receipt below rather than an opening-balance movement.
    mozzarella, mozzarella_created = await _get_or_create_item(
        session,
        name="Mozzarella cheese",
        actor=actor,
        category_id=categories["dairy"].id,
        base_unit_id=units["kilogram"].id,
        default_purchase_unit_id=units["kilogram"].id,
        default_location_id=locations["cold-storage"].id,
        preferred_supplier_id=suppliers["Nandi Dairy Foods"].id,
        reorder_level=Decimal("12"),
        reorder_quantity=Decimal("33"),
        target_stock=Decimal("45"),
        minimum_stock=Decimal("0.000"),
        lead_time_days=suppliers["Nandi Dairy Foods"].normal_lead_time_days,
        shelf_life_days=10,
        is_perishable=True,
        requires_batch_tracking=True,
        requires_expiry_tracking=True,
    )
    items["Mozzarella cheese"] = mozzarella

    paneer_patties, _ = await _get_or_create_item(
        session,
        name="Paneer burger patties",
        actor=actor,
        category_id=categories["proteins"].id,
        base_unit_id=units["piece"].id,
        default_purchase_unit_id=units["piece"].id,
        default_location_id=locations["cold-storage"].id,
        preferred_supplier_id=suppliers["Nandi Dairy Foods"].id,
        reorder_level=Decimal("40"),
        reorder_quantity=Decimal("110"),
        target_stock=Decimal("150"),
        minimum_stock=Decimal("0.000"),
        lead_time_days=suppliers["Nandi Dairy Foods"].normal_lead_time_days,
        shelf_life_days=7,
        is_perishable=True,
        requires_batch_tracking=True,
        requires_expiry_tracking=True,
    )
    items["Paneer burger patties"] = paneer_patties

    cheddar, _ = await _get_or_create_item(
        session,
        name="Cheddar slices",
        actor=actor,
        category_id=categories["dairy"].id,
        base_unit_id=units["piece"].id,
        default_purchase_unit_id=units["piece"].id,
        default_location_id=locations["cold-storage"].id,
        preferred_supplier_id=suppliers["Nandi Dairy Foods"].id,
        reorder_level=Decimal("120"),
        reorder_quantity=Decimal("380"),
        target_stock=Decimal("500"),
        minimum_stock=Decimal("0.000"),
        lead_time_days=suppliers["Nandi Dairy Foods"].normal_lead_time_days,
        shelf_life_days=21,
        is_perishable=True,
        requires_batch_tracking=False,
        requires_expiry_tracking=False,
    )
    items["Cheddar slices"] = cheddar

    return items


# --- Stock operation examples --------------------------------------------


async def _seed_receipt(
    session: AsyncSession,
    *,
    items: dict[str, InventoryItem],
    locations: dict[str, StorageLocation],
    suppliers: dict[str, Supplier],
    units: dict[str, UnitOfMeasure],
    actor: StaffUser,
) -> None:
    """One posted purchase receipt (this phase's required example),
    covering the entire opening stock of the two batch/expiry-tracked items
    plus one plain dairy line — see `_RECEIPT_ITEM_NAMES`.

    Mozzarella cheese's batch expires in 3 days: the phase's required
    "expiring batch" dashboard example. Paneer burger patties' batch
    expires in 6 days, inside its own 7-day shelf life — realistic for a
    genuinely short-shelf-life ingredient just received.
    """
    existing = await session.scalar(
        select(StockReceipt).where(StockReceipt.supplier_reference == _SEED_RECEIPT_MARKER)
    )
    if existing is not None:
        return

    location = locations["cold-storage"]
    supplier = suppliers["Nandi Dairy Foods"]
    today = date.today()

    receipt = await receipts_service.create_receipt(
        session,
        actor=actor,
        supplier_id=supplier.id,
        storage_location_id=location.id,
        received_date=today,
        supplier_reference=_SEED_RECEIPT_MARKER,
        notes="Seed data: weekly dairy restock.",
    )

    await receipts_service.add_receipt_item(
        session,
        receipt=receipt,
        inventory_item_id=items["Mozzarella cheese"].id,
        purchase_unit_id=units["kilogram"].id,
        received_quantity=Decimal("38.500"),
        accepted_quantity=Decimal("38.500"),
        rejected_quantity=ZERO,
        unit_cost_minor=_minor(540),
        batch_code=f"MOZ-{today.isoformat()}",
        manufactured_at=today - timedelta(days=2),
        expires_at=today + timedelta(days=3),
        notes=None,
    )
    await receipts_service.add_receipt_item(
        session,
        receipt=receipt,
        inventory_item_id=items["Paneer burger patties"].id,
        purchase_unit_id=units["piece"].id,
        received_quantity=Decimal("120"),
        accepted_quantity=Decimal("120"),
        rejected_quantity=ZERO,
        unit_cost_minor=_minor(58),
        batch_code=f"PBP-{today.isoformat()}",
        manufactured_at=today - timedelta(days=1),
        expires_at=today + timedelta(days=6),
        notes=None,
    )
    await receipts_service.add_receipt_item(
        session,
        receipt=receipt,
        inventory_item_id=items["Cheddar slices"].id,
        purchase_unit_id=units["piece"].id,
        received_quantity=Decimal("390"),
        accepted_quantity=Decimal("390"),
        rejected_quantity=ZERO,
        unit_cost_minor=_minor(16),
        batch_code=None,
        manufactured_at=None,
        expires_at=None,
        notes=None,
    )

    await receipts_service.post_receipt(session, actor=actor, receipt=receipt, request=None)


async def _seed_adjustment(
    session: AsyncSession,
    *,
    items: dict[str, InventoryItem],
    locations: dict[str, StorageLocation],
    actor: StaffUser,
) -> None:
    """One negative adjustment (this phase's required example) sized to
    also serve as the required critical/low-stock dashboard example:
    Mushrooms (8 kg on hand, 3 kg reorder level) drops to 1.5 kg, at the
    critical threshold (half the reorder level).
    """
    idempotency_key = "seed-adjustment-mushrooms"
    if await ledger.find_by_idempotency_key(session, idempotency_key) is not None:
        return
    await adjustments_service.create_adjustment(
        session,
        actor=actor,
        inventory_item_id=items["Mushrooms"].id,
        storage_location_id=locations["cold-storage"].id,
        batch_id=None,
        direction="decrease",
        quantity=Decimal("6.500"),
        reason_category="spoiled",
        reason=(
            "Seed data: a refrigeration fluctuation overnight spoiled most of the "
            "mushroom stock; corrected after morning inspection."
        ),
        approved_by=actor.id,
        idempotency_key=idempotency_key,
        request=None,
    )


async def _seed_wastage(
    session: AsyncSession,
    *,
    items: dict[str, InventoryItem],
    locations: dict[str, StorageLocation],
    actor: StaffUser,
) -> None:
    """One wastage record (this phase's required example) sized to also
    serve as the required out-of-stock dashboard example: the entire
    18 kg of black beans is discarded, taking on-hand to zero.
    """
    idempotency_key = "seed-wastage-black-beans"
    if await ledger.find_by_idempotency_key(session, idempotency_key) is not None:
        return
    await wastage_service.record_wastage(
        session,
        actor=actor,
        inventory_item_id=items["Black beans"].id,
        storage_location_id=locations["dry-store"].id,
        batch_id=None,
        quantity=Decimal("18.000"),
        reason_category="spoilage",
        reason="Seed data: entire batch of black beans found spoiled during morning prep check.",
        station="Dry Store",
        related_order_id=None,
        approved_by=actor.id,
        idempotency_key=idempotency_key,
        request=None,
    )


async def _seed_transfer(
    session: AsyncSession,
    *,
    items: dict[str, InventoryItem],
    locations: dict[str, StorageLocation],
    actor: StaffUser,
) -> None:
    """One posted transfer (this phase's required example): 5 litres of
    cooking oil moved from Dry Store to Main Kitchen to top up working
    stock at the line.
    """
    existing = await session.scalar(
        select(StockTransfer).where(StockTransfer.notes == _SEED_TRANSFER_MARKER)
    )
    if existing is not None:
        return

    transfer = await transfers_service.create_transfer(
        session,
        actor=actor,
        source_location_id=locations["dry-store"].id,
        destination_location_id=locations["main-kitchen"].id,
        notes=_SEED_TRANSFER_MARKER,
    )
    await transfers_service.add_transfer_item(
        session,
        transfer=transfer,
        inventory_item_id=items["Cooking oil"].id,
        batch_id=None,
        quantity=Decimal("5.000"),
        notes="Seed data: top up kitchen working stock.",
    )
    await transfers_service.post_transfer(session, actor=actor, transfer=transfer, request=None)


async def _seed_stock_count(
    session: AsyncSession,
    *,
    locations: dict[str, StorageLocation],
    actor: StaffUser,
) -> None:
    """One approved stock-count session (this phase's required example) at
    the Bar location — its two items (cola syrup, mineral water bottles)
    keep the line count small and reviewable. Mineral water bottles is
    deliberately counted 5 short of system stock, exercising the variance
    -> `stock_count_adjustment` approval path end to end.
    """
    existing = await session.scalar(
        select(StockCount).where(StockCount.notes == _SEED_COUNT_MARKER)
    )
    if existing is not None:
        return

    location = locations["bar"]
    count = await stock_counts_service.create_count(
        session,
        actor=actor,
        storage_location_id=location.id,
        scheduled_date=date.today(),
        notes=_SEED_COUNT_MARKER,
    )
    count = await stock_counts_service.start_count(session, actor=actor, count=count)

    lines = (
        await session.scalars(select(StockCountLine).where(StockCountLine.count_id == count.id))
    ).all()
    for line in lines:
        item = await session.get(InventoryItem, line.inventory_item_id)
        assert item is not None
        counted = (
            line.system_quantity - Decimal("5")
            if item.name == "Mineral water bottles"
            else (line.system_quantity)
        )
        await stock_counts_service.record_count_line(
            session,
            count=count,
            line=line,
            counted_quantity=counted,
            reason="Seed data: routine bar cycle count."
            if item.name == "Mineral water bottles"
            else None,
            notes=None,
        )

    count = await stock_counts_service.submit_count(session, actor=actor, count=count, request=None)
    await stock_counts_service.approve_count(session, actor=actor, count=count, request=None)


# --- Recipes --------------------------------------------------------------


async def _product_id(session: AsyncSession, name: str) -> uuid.UUID | None:
    result = await session.scalar(select(Product.id).where(Product.name == name))
    return result


async def _variant_id(session: AsyncSession, product_id: uuid.UUID, name: str) -> uuid.UUID | None:
    result = await session.scalar(
        select(ProductVariant.id).where(
            ProductVariant.product_id == product_id, ProductVariant.name == name
        )
    )
    return result


async def _seed_recipe(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product_id: uuid.UUID,
    variant_id: uuid.UUID | None,
    yield_unit_id: uuid.UUID,
    ingredients: tuple[tuple[str, InventoryItem, Decimal, uuid.UUID], ...],
) -> None:
    existing = await recipes_service.resolve_recipe(
        session, product_id=product_id, variant_id=variant_id, as_of=datetime.now(UTC)
    )
    if existing is not None:
        return

    recipe = await recipes_service.create_recipe(
        session,
        actor=actor,
        product_id=product_id,
        variant_id=variant_id,
        yield_quantity=Decimal("1"),
        yield_unit_id=yield_unit_id,
        preparation_loss_percentage=Decimal("0.00"),
        effective_from=datetime.now(UTC),
        notes="Seed data.",
    )
    for display_order, (_label, item, quantity, unit_id) in enumerate(ingredients):
        await recipes_service.add_recipe_item(
            session,
            recipe=recipe,
            inventory_item_id=item.id,
            quantity_required=quantity,
            unit_id=unit_id,
            waste_factor=Decimal("0.00"),
            storage_location_id=None,
            display_order=display_order,
            notes=None,
        )


async def _seed_recipes(
    session: AsyncSession,
    *,
    items: dict[str, InventoryItem],
    units: dict[str, UnitOfMeasure],
    actor: StaffUser,
) -> None:
    piece = units["piece"].id
    kg = units["kilogram"].id
    litre = units["litre"].id

    classic_veg_burger = await _product_id(session, "RKPR Classic Veg Burger")
    bbq_chicken_burger = await _product_id(session, "Smoky BBQ Chicken Burger")
    margherita = await _product_id(session, "Margherita Pizza")
    crispy_veg_taco = await _product_id(session, "Crispy Veg Taco")

    if classic_veg_burger is not None:
        await _seed_recipe(
            session,
            actor=actor,
            product_id=classic_veg_burger,
            variant_id=None,
            yield_unit_id=piece,
            ingredients=(
                ("bun", items["Burger buns"], Decimal("1"), piece),
                ("patty", items["Vegetable burger patties"], Decimal("1"), piece),
                ("lettuce", items["Lettuce"], Decimal("0.020"), kg),
                ("tomato", items["Tomatoes"], Decimal("0.020"), kg),
                ("onion", items["Onions"], Decimal("0.015"), kg),
                ("pickles", items["Pickles"], Decimal("0.010"), kg),
                ("sauce", items["Burger sauce"], Decimal("0.020"), litre),
            ),
        )

    if bbq_chicken_burger is not None:
        await _seed_recipe(
            session,
            actor=actor,
            product_id=bbq_chicken_burger,
            variant_id=None,
            yield_unit_id=piece,
            ingredients=(
                ("bun", items["Burger buns"], Decimal("1"), piece),
                ("patty", items["Chicken burger patties"], Decimal("1"), piece),
                ("sauce", items["Barbecue sauce"], Decimal("0.025"), litre),
                ("onion", items["Onions"], Decimal("0.020"), kg),
                ("lettuce", items["Lettuce"], Decimal("0.015"), kg),
                ("cheese", items["Cheddar slices"], Decimal("1"), piece),
            ),
        )

    if margherita is not None:
        eight_inch = await _variant_id(session, margherita, "8-inch")
        eleven_inch = await _variant_id(session, margherita, "11-inch")
        if eight_inch is not None:
            await _seed_recipe(
                session,
                actor=actor,
                product_id=margherita,
                variant_id=eight_inch,
                yield_unit_id=piece,
                ingredients=(
                    ("dough", items["Pizza dough balls, small"], Decimal("1"), piece),
                    ("sauce", items["Tomato pizza sauce"], Decimal("0.080"), litre),
                    ("cheese", items["Mozzarella cheese"], Decimal("0.120"), kg),
                ),
            )
        if eleven_inch is not None:
            await _seed_recipe(
                session,
                actor=actor,
                product_id=margherita,
                variant_id=eleven_inch,
                yield_unit_id=piece,
                ingredients=(
                    ("dough", items["Pizza dough balls, large"], Decimal("1"), piece),
                    ("sauce", items["Tomato pizza sauce"], Decimal("0.140"), litre),
                    ("cheese", items["Mozzarella cheese"], Decimal("0.220"), kg),
                ),
            )

    if crispy_veg_taco is not None:
        await _seed_recipe(
            session,
            actor=actor,
            product_id=crispy_veg_taco,
            variant_id=None,
            yield_unit_id=piece,
            ingredients=(
                ("shells", items["Taco shells"], Decimal("2"), piece),
                ("beans", items["Black beans"], Decimal("0.030"), kg),
                ("lettuce", items["Lettuce"], Decimal("0.020"), kg),
                ("cheese", items["Cheddar slices"], Decimal("2"), piece),
            ),
        )


async def seed_inventory(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    units = await _seed_units(session, actor=actor)
    categories = await _seed_categories(session, actor=actor)
    locations = await _seed_locations(session, actor=actor)
    suppliers = await _seed_suppliers(session, actor=actor)
    items = await _seed_items(
        session,
        units=units,
        categories=categories,
        locations=locations,
        suppliers=suppliers,
        actor=actor,
    )

    await _seed_receipt(
        session, items=items, locations=locations, suppliers=suppliers, units=units, actor=actor
    )
    await _seed_adjustment(session, items=items, locations=locations, actor=actor)
    await _seed_wastage(session, items=items, locations=locations, actor=actor)
    await _seed_transfer(session, items=items, locations=locations, actor=actor)
    await _seed_stock_count(session, locations=locations, actor=actor)
    await _seed_recipes(session, items=items, units=units, actor=actor)
