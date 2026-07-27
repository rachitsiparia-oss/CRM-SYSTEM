"""Exact-decimal unit conversion.

This phase's own instruction, verbatim: "Only allow conversions within
compatible unit types. Do not allow conversions such as kilograms to litres.
Do not invent density-based conversion in this phase. All conversion factors
must use exact decimal storage."

Every quantity in this module is a `decimal.Decimal`. Nothing here ever
touches `float` — a binary float cannot represent 0.1 exactly, and an
inventory ledger that drifts by fractions of a gram per movement is
unauditable. `QUANTITY_EXPONENT` matches the NUMERIC(16,3) storage every
ledger column uses, so a converted value always round-trips to the database
unchanged.
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal, localcontext

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UnitOfMeasure
from app.inventory.errors import IncompatibleUnitError, MissingConversionError

# NUMERIC(16,3) — three decimal places, matching every quantity column.
QUANTITY_EXPONENT = Decimal("0.001")

# Conversion arithmetic runs at high precision and is only rounded once, at
# the end, to the storage scale. Rounding intermediate steps would compound
# error across a multi-ingredient recipe explosion.
_CONVERSION_PRECISION = 34


def quantize_quantity(value: Decimal) -> Decimal:
    """Round a quantity to the stored scale, half-up.

    Half-up (not banker's rounding) is chosen deliberately and documented in
    DATABASE_AND_API.md section 9.8: it is what a stock keeper expects when
    reading a printed figure, and it is the same rule the costing module
    applies to money, so quantities and values round consistently.
    """
    return value.quantize(QUANTITY_EXPONENT, rounding=ROUND_HALF_UP)


async def get_unit(session: AsyncSession, unit_id: uuid.UUID) -> UnitOfMeasure:
    unit = await session.get(UnitOfMeasure, unit_id)
    if unit is None:
        raise MissingConversionError(f"Unit of measure {unit_id} was not found.")
    return unit


async def load_units(
    session: AsyncSession, unit_ids: set[uuid.UUID]
) -> dict[uuid.UUID, UnitOfMeasure]:
    """Batch-load units so a recipe explosion or a multi-line receipt does
    not issue one query per line (CLAUDE.md section 5.2, avoid N+1)."""
    if not unit_ids:
        return {}
    rows = (
        await session.scalars(select(UnitOfMeasure).where(UnitOfMeasure.id.in_(unit_ids)))
    ).all()
    found = {unit.id: unit for unit in rows}
    missing = unit_ids - found.keys()
    if missing:
        raise MissingConversionError(
            f"Unknown unit of measure: {', '.join(sorted(str(m) for m in missing))}."
        )
    return found


def assert_compatible(from_unit: UnitOfMeasure, to_unit: UnitOfMeasure) -> None:
    """Reject cross-type conversion (the kilograms-to-litres case).

    Converting weight to volume needs the density of the specific substance,
    which this project does not model — this phase's instruction explicitly
    forbids inventing it. Failing loudly is the only correct behavior: a
    silent wrong answer here would corrupt stock quantities.
    """
    if from_unit.unit_type != to_unit.unit_type:
        raise IncompatibleUnitError(
            f"Cannot convert {from_unit.symbol} ({from_unit.unit_type}) to "
            f"{to_unit.symbol} ({to_unit.unit_type}): units measure different "
            "physical properties, and density-based conversion is not supported."
        )


def convert(quantity: Decimal, from_unit: UnitOfMeasure, to_unit: UnitOfMeasure) -> Decimal:
    """Convert `quantity` from one unit to another of the same unit type.

    Both units' `conversion_factor` is "how many base units is one of me", so
    the conversion is a single ratio and needs no knowledge of which unit is
    the base:

        base_amount = quantity * from.conversion_factor
        result      = base_amount / to.conversion_factor

    e.g. 2.5 kg -> g with kg.factor=1000, g.factor=1:
        (2.5 * 1000) / 1 == 2500.000
    """
    assert_compatible(from_unit, to_unit)
    if from_unit.id == to_unit.id:
        return quantize_quantity(quantity)

    with localcontext() as ctx:
        ctx.prec = _CONVERSION_PRECISION
        base_amount = quantity * from_unit.conversion_factor
        converted = base_amount / to_unit.conversion_factor
    return quantize_quantity(converted)


async def convert_by_id(
    session: AsyncSession,
    quantity: Decimal,
    from_unit_id: uuid.UUID,
    to_unit_id: uuid.UUID,
) -> Decimal:
    if from_unit_id == to_unit_id:
        return quantize_quantity(quantity)
    units = await load_units(session, {from_unit_id, to_unit_id})
    return convert(quantity, units[from_unit_id], units[to_unit_id])


def convert_purchase_quantity(
    quantity: Decimal,
    *,
    purchase_unit: UnitOfMeasure,
    base_unit: UnitOfMeasure,
    purchase_conversion_factor: Decimal | None,
) -> Decimal:
    """Convert a purchased quantity into an item's base unit.

    Two distinct cases, and conflating them is a real source of stock errors:

    1. The purchase unit and base unit share a unit type (buy in kilograms,
       stock in grams) — an ordinary `convert()`.
    2. The purchase unit is a *packaging* unit whose size is a property of
       this item, not of the unit itself (buy a "box", stock in "pieces";
       a box of buns and a box of napkins hold different counts). The unit
       table cannot express that, so the item carries
       `purchase_conversion_factor` = base units per purchase unit.

    Case 2 is only consulted when the units are genuinely incompatible or the
    item explicitly overrides the ratio, and a missing factor raises rather
    than silently guessing 1:1.
    """
    if purchase_unit.id == base_unit.id:
        return quantize_quantity(quantity)

    if purchase_unit.unit_type == base_unit.unit_type and purchase_conversion_factor is None:
        return convert(quantity, purchase_unit, base_unit)

    if purchase_conversion_factor is None:
        raise MissingConversionError(
            f"No conversion from {purchase_unit.symbol} to {base_unit.symbol} for this item: "
            "set the item's purchase-to-base conversion factor."
        )

    with localcontext() as ctx:
        ctx.prec = _CONVERSION_PRECISION
        converted = quantity * purchase_conversion_factor
    return quantize_quantity(converted)
