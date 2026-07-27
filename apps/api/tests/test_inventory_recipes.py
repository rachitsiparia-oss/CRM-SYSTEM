"""Recipe resolution and costing — `app.inventory.recipes`.

Covers the resolution policy (exact variant match wins, falls back to the
product's base recipe, respects the effective window) and the costing
policy (waste factor inflates required quantity, preparation loss reduces
usable yield, missing cost data is reported rather than guessed).
"""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.db.models import MenuCategory, Product, ProductVariant, StaffUser
from app.inventory import recipes as recipes_service
from app.inventory.errors import InactiveRecipeError
from sqlalchemy.ext.asyncio import AsyncSession

from tests._inventory_helpers import make_item, make_unit

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def _make_product(
    session: AsyncSession, *, price_minor: int = 10000, **overrides: object
) -> Product:
    suffix = uuid.uuid4().hex[:10]
    category = MenuCategory(id=uuid.uuid4(), code=f"cat-{suffix}", name="Test Category")
    session.add(category)
    await session.flush()
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "product_code": f"PROD-{suffix}",
        "category_id": category.id,
        "name": f"Product {suffix}",
        "slug": f"product-{suffix}",
        "food_type": "vegetarian",
        "base_price_minor": price_minor,
    }
    fields.update(overrides)
    product = Product(**fields)
    session.add(product)
    await session.flush()
    return product


async def _make_variant(
    session: AsyncSession, product: Product, *, price_minor: int
) -> ProductVariant:
    suffix = uuid.uuid4().hex[:10]
    variant = ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        code=f"VAR-{suffix}",
        name="Large",
        price_minor=price_minor,
    )
    session.add(variant)
    await session.flush()
    return variant


# --- Resolution -------------------------------------------------------------


async def test_resolve_recipe_returns_none_when_no_recipe_exists(
    db_session: AsyncSession,
) -> None:
    product = await _make_product(db_session)
    result = await recipes_service.resolve_recipe(
        db_session, product_id=product.id, variant_id=None, as_of=datetime.now(UTC)
    )
    assert result is None


async def test_resolve_recipe_finds_base_recipe(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    recipe = await recipes_service.create_recipe(
        db_session,
        actor=actor,
        product_id=product.id,
        variant_id=None,
        yield_quantity=Decimal("1"),
        yield_unit_id=None,
        preparation_loss_percentage=Decimal("0"),
        effective_from=datetime.now(UTC) - timedelta(hours=1),
        notes=None,
    )
    resolved = await recipes_service.resolve_recipe(
        db_session, product_id=product.id, variant_id=None, as_of=datetime.now(UTC)
    )
    assert resolved is not None
    assert resolved.id == recipe.id


async def test_resolve_recipe_exact_variant_match_wins_over_base(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    variant = await _make_variant(db_session, product, price_minor=15000)

    base_recipe = await recipes_service.create_recipe(
        db_session,
        actor=actor,
        product_id=product.id,
        variant_id=None,
        yield_quantity=Decimal("1"),
        yield_unit_id=None,
        preparation_loss_percentage=Decimal("0"),
        effective_from=datetime.now(UTC) - timedelta(hours=1),
        notes=None,
    )
    variant_recipe = await recipes_service.create_recipe(
        db_session,
        actor=actor,
        product_id=product.id,
        variant_id=variant.id,
        yield_quantity=Decimal("1"),
        yield_unit_id=None,
        preparation_loss_percentage=Decimal("0"),
        effective_from=datetime.now(UTC) - timedelta(hours=1),
        notes=None,
    )

    resolved = await recipes_service.resolve_recipe(
        db_session, product_id=product.id, variant_id=variant.id, as_of=datetime.now(UTC)
    )
    assert resolved is not None
    assert resolved.id == variant_recipe.id
    assert resolved.id != base_recipe.id


async def test_resolve_recipe_falls_back_to_base_when_no_variant_recipe(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    variant = await _make_variant(db_session, product, price_minor=15000)

    base_recipe = await recipes_service.create_recipe(
        db_session,
        actor=actor,
        product_id=product.id,
        variant_id=None,
        yield_quantity=Decimal("1"),
        yield_unit_id=None,
        preparation_loss_percentage=Decimal("0"),
        effective_from=datetime.now(UTC) - timedelta(hours=1),
        notes=None,
    )

    resolved = await recipes_service.resolve_recipe(
        db_session, product_id=product.id, variant_id=variant.id, as_of=datetime.now(UTC)
    )
    assert resolved is not None
    assert resolved.id == base_recipe.id


async def test_resolve_recipe_respects_effective_window(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    await recipes_service.create_recipe(
        db_session,
        actor=actor,
        product_id=product.id,
        variant_id=None,
        yield_quantity=Decimal("1"),
        yield_unit_id=None,
        preparation_loss_percentage=Decimal("0"),
        effective_from=datetime.now(UTC) + timedelta(days=7),  # not yet effective
        notes=None,
    )
    resolved = await recipes_service.resolve_recipe(
        db_session, product_id=product.id, variant_id=None, as_of=datetime.now(UTC)
    )
    assert resolved is None


async def test_resolve_recipe_ignores_archived_recipe(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    recipe = await recipes_service.create_recipe(
        db_session,
        actor=actor,
        product_id=product.id,
        variant_id=None,
        yield_quantity=Decimal("1"),
        yield_unit_id=None,
        preparation_loss_percentage=Decimal("0"),
        effective_from=datetime.now(UTC) - timedelta(hours=1),
        notes=None,
    )
    await recipes_service.archive_recipe(db_session, actor=actor, recipe=recipe, request=None)

    resolved = await recipes_service.resolve_recipe(
        db_session, product_id=product.id, variant_id=None, as_of=datetime.now(UTC)
    )
    assert resolved is None


# --- Costing -----------------------------------------------------------------


async def test_recipe_cost_sums_ingredient_costs(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    unit = await make_unit(db_session, unit_type="count", decimal_places=0)
    ingredient = await make_item(
        db_session, base_unit_id=unit.id, standard_cost_minor=200
    )  # 2.00 per unit
    product = await _make_product(db_session, price_minor=1000)

    recipe = await recipes_service.create_recipe(
        db_session,
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
        db_session,
        recipe=recipe,
        inventory_item_id=ingredient.id,
        quantity_required=Decimal("3"),
        unit_id=unit.id,
        waste_factor=Decimal("0"),
        storage_location_id=None,
        display_order=0,
        notes=None,
    )

    cost = await recipes_service.calculate_recipe_cost(db_session, recipe=recipe)
    assert cost.total_ingredient_cost_minor == 600  # 3 * 200
    assert cost.cost_per_yield_minor == 600
    assert cost.selling_price_minor == 1000
    assert cost.gross_margin_minor == 400
    assert cost.missing_cost_item_names == []


async def test_recipe_cost_waste_factor_inflates_effective_quantity(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    unit = await make_unit(db_session, unit_type="count", decimal_places=0)
    ingredient = await make_item(db_session, base_unit_id=unit.id, standard_cost_minor=100)
    product = await _make_product(db_session)

    recipe = await recipes_service.create_recipe(
        db_session,
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
        db_session,
        recipe=recipe,
        inventory_item_id=ingredient.id,
        quantity_required=Decimal("10"),
        unit_id=unit.id,
        waste_factor=Decimal("0.20"),  # 20% waste -> 10 / 0.8 = 12.5 effective
        storage_location_id=None,
        display_order=0,
        notes=None,
    )

    cost = await recipes_service.calculate_recipe_cost(db_session, recipe=recipe)
    assert cost.ingredients[0].effective_quantity == Decimal("12.500")
    assert cost.total_ingredient_cost_minor == 1250  # 12.5 * 100


async def test_recipe_cost_preparation_loss_reduces_effective_yield(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    unit = await make_unit(db_session, unit_type="count", decimal_places=0)
    ingredient = await make_item(db_session, base_unit_id=unit.id, standard_cost_minor=100)
    product = await _make_product(db_session)

    recipe = await recipes_service.create_recipe(
        db_session,
        actor=actor,
        product_id=product.id,
        variant_id=None,
        yield_quantity=Decimal("10"),
        yield_unit_id=unit.id,
        preparation_loss_percentage=Decimal("20"),  # 10 * 0.8 = 8 effective yield
        effective_from=datetime.now(UTC) - timedelta(hours=1),
        notes=None,
    )
    await recipes_service.add_recipe_item(
        db_session,
        recipe=recipe,
        inventory_item_id=ingredient.id,
        quantity_required=Decimal("80"),
        unit_id=unit.id,
        waste_factor=Decimal("0"),
        storage_location_id=None,
        display_order=0,
        notes=None,
    )

    cost = await recipes_service.calculate_recipe_cost(db_session, recipe=recipe)
    assert cost.effective_yield == Decimal("8.000")
    assert cost.total_ingredient_cost_minor == 8000  # 80 * 100
    assert cost.cost_per_yield_minor == 1000  # 8000 / 8


async def test_recipe_cost_reports_missing_cost_without_guessing(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    unit = await make_unit(db_session, unit_type="count", decimal_places=0)
    ingredient = await make_item(
        db_session, base_unit_id=unit.id, standard_cost_minor=None, latest_purchase_cost_minor=None
    )
    product = await _make_product(db_session)

    recipe = await recipes_service.create_recipe(
        db_session,
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
        db_session,
        recipe=recipe,
        inventory_item_id=ingredient.id,
        quantity_required=Decimal("1"),
        unit_id=unit.id,
        waste_factor=Decimal("0"),
        storage_location_id=None,
        display_order=0,
        notes=None,
    )

    cost = await recipes_service.calculate_recipe_cost(db_session, recipe=recipe)
    assert cost.total_ingredient_cost_minor is None
    assert ingredient.name in cost.missing_cost_item_names


async def test_recipe_cost_falls_back_to_latest_purchase_cost(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    unit = await make_unit(db_session, unit_type="count", decimal_places=0)
    ingredient = await make_item(
        db_session, base_unit_id=unit.id, standard_cost_minor=None, latest_purchase_cost_minor=150
    )
    product = await _make_product(db_session)

    recipe = await recipes_service.create_recipe(
        db_session,
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
        db_session,
        recipe=recipe,
        inventory_item_id=ingredient.id,
        quantity_required=Decimal("2"),
        unit_id=unit.id,
        waste_factor=Decimal("0"),
        storage_location_id=None,
        display_order=0,
        notes=None,
    )

    cost = await recipes_service.calculate_recipe_cost(db_session, recipe=recipe)
    assert cost.total_ingredient_cost_minor == 300  # 2 * 150
    assert cost.ingredients[0].cost_source == "latest_purchase"


async def test_recipe_cost_rejects_inactive_recipe(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    product = await _make_product(db_session)
    recipe = await recipes_service.create_recipe(
        db_session,
        actor=actor,
        product_id=product.id,
        variant_id=None,
        yield_quantity=Decimal("1"),
        yield_unit_id=None,
        preparation_loss_percentage=Decimal("0"),
        effective_from=datetime.now(UTC) - timedelta(hours=1),
        notes=None,
    )
    await recipes_service.archive_recipe(db_session, actor=actor, recipe=recipe, request=None)

    with pytest.raises(InactiveRecipeError):
        await recipes_service.calculate_recipe_cost(db_session, recipe=recipe)
