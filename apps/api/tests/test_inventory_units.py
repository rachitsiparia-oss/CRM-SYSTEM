"""Exact-decimal unit conversion — `app.inventory.units`.

This phase's own instruction, verbatim: "Only allow conversions within
compatible unit types... All conversion factors must use exact decimal
storage." These tests exercise the compatible/incompatible cases and the
packaging-unit purchase-conversion path directly against Decimal math, with
no floating point anywhere.
"""

from decimal import Decimal

import pytest
from app.inventory.errors import IncompatibleUnitError, MissingConversionError
from app.inventory.units import (
    assert_compatible,
    convert,
    convert_purchase_quantity,
    quantize_quantity,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests._inventory_helpers import make_unit, make_weight_units

# No module-level `pytestmark = pytest.mark.asyncio`: this file mixes sync
# and async tests, and `asyncio_mode = "auto"` (pyproject.toml) already
# detects `async def` tests on its own — an explicit mark on every test
# would incorrectly flag the sync ones too.


def test_quantize_quantity_rounds_half_up() -> None:
    assert quantize_quantity(Decimal("1.2345")) == Decimal("1.235")
    assert quantize_quantity(Decimal("1.2344")) == Decimal("1.234")
    assert quantize_quantity(Decimal("1.0005")) == Decimal("1.001")


async def test_convert_kilogram_to_gram_is_exact(db_session: AsyncSession) -> None:
    gram, kilogram = await make_weight_units(db_session)
    result = convert(Decimal("2.5"), kilogram, gram)
    assert result == Decimal("2500.000")


async def test_convert_gram_to_kilogram_is_exact(db_session: AsyncSession) -> None:
    gram, kilogram = await make_weight_units(db_session)
    result = convert(Decimal("2500"), gram, kilogram)
    assert result == Decimal("2.500")


async def test_convert_same_unit_is_identity(db_session: AsyncSession) -> None:
    gram, _kilogram = await make_weight_units(db_session)
    assert convert(Decimal("3.333"), gram, gram) == Decimal("3.333")


async def test_convert_rejects_cross_type(db_session: AsyncSession) -> None:
    _gram, kilogram = await make_weight_units(db_session)
    millilitre = await make_unit(db_session, unit_type="volume")
    with pytest.raises(IncompatibleUnitError):
        convert(Decimal("1"), kilogram, millilitre)


def test_assert_compatible_rejects_weight_and_volume() -> None:
    from app.db.models import UnitOfMeasure

    weight = UnitOfMeasure(unit_type="weight", conversion_factor=Decimal("1"))
    volume = UnitOfMeasure(unit_type="volume", conversion_factor=Decimal("1"))
    with pytest.raises(IncompatibleUnitError):
        assert_compatible(weight, volume)


def test_assert_compatible_allows_same_type() -> None:
    from app.db.models import UnitOfMeasure

    a = UnitOfMeasure(unit_type="weight", conversion_factor=Decimal("1"))
    b = UnitOfMeasure(unit_type="weight", conversion_factor=Decimal("1000"))
    assert_compatible(a, b)  # does not raise


# --- convert_purchase_quantity: the packaging-unit case --------------------


async def test_purchase_conversion_same_unit_is_identity(db_session: AsyncSession) -> None:
    piece = await make_unit(db_session, unit_type="count", decimal_places=0)
    result = convert_purchase_quantity(
        Decimal("42"), purchase_unit=piece, base_unit=piece, purchase_conversion_factor=None
    )
    assert result == Decimal("42.000")


async def test_purchase_conversion_uses_ordinary_convert_for_compatible_units(
    db_session: AsyncSession,
) -> None:
    gram, kilogram = await make_weight_units(db_session)
    result = convert_purchase_quantity(
        Decimal("3"), purchase_unit=kilogram, base_unit=gram, purchase_conversion_factor=None
    )
    assert result == Decimal("3000.000")


async def test_purchase_conversion_same_type_without_override_uses_unit_factor(
    db_session: AsyncSession,
) -> None:
    """Two same-`unit_type` units (e.g. two "count" units) with no explicit
    `purchase_conversion_factor` fall through to an ordinary `convert()`
    using each unit's own generic factor — this is why an item purchased in
    a packaging unit whose ratio isn't universal (a box of buns vs. a box
    of napkins) MUST set `purchase_conversion_factor` explicitly; nothing
    else would catch a missing override for same-type units."""
    piece = await make_unit(db_session, unit_type="count", decimal_places=0)
    box = await make_unit(
        db_session, unit_type="count", base_unit_id=piece.id, conversion_factor=Decimal("1")
    )
    result = convert_purchase_quantity(
        Decimal("2"), purchase_unit=box, base_unit=piece, purchase_conversion_factor=None
    )
    assert result == Decimal("2.000")


async def test_purchase_conversion_cross_type_without_override_raises(
    db_session: AsyncSession,
) -> None:
    """A genuinely cross-type purchase/base unit pair (weight vs. count)
    with no explicit factor has no correct interpretation at all and must
    raise rather than guess."""
    piece = await make_unit(db_session, unit_type="count", decimal_places=0)
    kilogram = await make_unit(db_session, unit_type="weight")
    with pytest.raises(MissingConversionError):
        convert_purchase_quantity(
            Decimal("2"), purchase_unit=kilogram, base_unit=piece, purchase_conversion_factor=None
        )


async def test_purchase_conversion_applies_item_specific_factor(
    db_session: AsyncSession,
) -> None:
    piece = await make_unit(db_session, unit_type="count", decimal_places=0)
    packet = await make_unit(
        db_session, unit_type="count", base_unit_id=piece.id, conversion_factor=Decimal("1")
    )
    result = convert_purchase_quantity(
        Decimal("3"),
        purchase_unit=packet,
        base_unit=piece,
        purchase_conversion_factor=Decimal("20"),
    )
    assert result == Decimal("60.000")
