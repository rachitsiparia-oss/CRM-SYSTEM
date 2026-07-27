"""Recipe management and deterministic costing.

**Recipe resolution policy** — see `Recipe`'s own docstring for the full
reasoning; summarized here because `resolve_recipe` is the single call site
every other module (order integration, the costing below, the frontend
lookup endpoint) goes through: an exact `(product_id, variant_id)` match
wins, otherwise the product's base recipe `(variant_id IS NULL)` applies.
Only a recipe whose `[effective_from, effective_to)` window contains the
requested instant is considered, so a scheduled future recipe change can
never retroactively affect an order processed before it took effect.

**Costing policy** (this phase's own instruction: "Use the configured
inventory costing policy from the documentation... If costing policy is not
explicit, do not silently invent complex accounting behavior. Use the
existing standard/latest cost field appropriate to the project and record
the decision" — DATABASE_AND_API.md section 8.18 requires a valuation
method to be "explicitly configured and consistently applied" but does not
name one, so this is that explicit choice, recorded in DATABASE_AND_API.md
section 9.8):

  1. Each ingredient's cost basis is `inventory_items.standard_cost_minor`,
     falling back to `latest_purchase_cost_minor` when no standard cost has
     been set yet. Weighted-average costing is not implemented — the
     column exists on `InventoryItem` for a later phase, but nothing here
     writes or reads it, so introducing it into cost math now would be the
     "invent complex accounting behavior" this instruction forbids.
  2. Per-ingredient waste (`recipe_items.waste_factor`) inflates the
     quantity actually needed: `effective_quantity = base_quantity /
     (1 - waste_factor)`.
  3. The recipe's own `preparation_loss_percentage` (loss on the *finished*
     output — reduction, trim after cooking) reduces the usable yield:
     `effective_yield = yield_quantity * (1 - preparation_loss_percentage
     / 100)`.
  4. `cost_per_yield_minor = round(total_ingredient_cost_minor /
     effective_yield)`. Since `yield_quantity` is documented as "how many
     sellable units one execution produces," this is also the cost per
     sellable unit — no further division.

All rounding is ROUND_HALF_UP on the final integer minor-unit figure only;
intermediate ingredient-cost sums are kept as exact Decimal so the
calculation is reproducible regardless of ingredient order.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import (
    InventoryItem,
    Product,
    ProductVariant,
    Recipe,
    RecipeItem,
    StaffUser,
    UnitOfMeasure,
)
from app.inventory.errors import InactiveRecipeError, MissingRecipeError
from app.inventory.units import assert_compatible, convert, quantize_quantity

ZERO = Decimal("0.000")


def generate_recipe_code() -> str:
    return f"RCP-CODE-{uuid.uuid4().hex[:8].upper()}"


async def resolve_recipe(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    variant_id: uuid.UUID | None,
    as_of: datetime,
) -> Recipe | None:
    """Return the recipe that governs `(product_id, variant_id)` at `as_of`,
    or None if none applies. See module docstring for the resolution order.
    """
    effective_window = (
        Recipe.effective_from <= as_of,
        (Recipe.effective_to.is_(None)) | (Recipe.effective_to > as_of),
    )

    if variant_id is not None:
        exact = await session.scalar(
            select(Recipe).where(
                Recipe.product_id == product_id,
                Recipe.variant_id == variant_id,
                Recipe.is_active.is_(True),
                Recipe.deleted_at.is_(None),
                *effective_window,
            )
        )
        if exact is not None:
            return exact

    base = await session.scalar(
        select(Recipe).where(
            Recipe.product_id == product_id,
            Recipe.variant_id.is_(None),
            Recipe.is_active.is_(True),
            Recipe.deleted_at.is_(None),
            *effective_window,
        )
    )
    return base


async def require_recipe(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    variant_id: uuid.UUID | None,
    as_of: datetime,
) -> Recipe:
    recipe = await resolve_recipe(
        session, product_id=product_id, variant_id=variant_id, as_of=as_of
    )
    if recipe is None:
        raise MissingRecipeError(
            f"No active recipe is defined for product {product_id}"
            + (f", variant {variant_id}" if variant_id else "")
            + "."
        )
    return recipe


async def create_recipe(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product_id: uuid.UUID,
    variant_id: uuid.UUID | None,
    yield_quantity: Decimal,
    yield_unit_id: uuid.UUID | None,
    preparation_loss_percentage: Decimal,
    effective_from: datetime,
    notes: str | None,
) -> Recipe:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    if variant_id is not None:
        variant = await session.get(ProductVariant, variant_id)
        if variant is None or variant.product_id != product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Variant does not belong to the selected product.",
            )

    recipe = Recipe(
        id=uuid.uuid4(),
        recipe_code=generate_recipe_code(),
        product_id=product_id,
        variant_id=variant_id,
        yield_quantity=quantize_quantity(yield_quantity),
        yield_unit_id=yield_unit_id,
        preparation_loss_percentage=preparation_loss_percentage,
        is_active=True,
        effective_from=effective_from,
        notes=notes,
        created_by=actor.id,
    )
    session.add(recipe)
    await session.flush()
    return recipe


async def add_recipe_item(
    session: AsyncSession,
    *,
    recipe: Recipe,
    inventory_item_id: uuid.UUID,
    quantity_required: Decimal,
    unit_id: uuid.UUID,
    waste_factor: Decimal,
    storage_location_id: uuid.UUID | None,
    display_order: int,
    notes: str | None,
) -> RecipeItem:
    item = await session.get(InventoryItem, inventory_item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found."
        )
    unit = await session.get(UnitOfMeasure, unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")
    base_unit = await session.get(UnitOfMeasure, item.base_unit_id)
    assert base_unit is not None
    assert_compatible(unit, base_unit)

    base_quantity = convert(quantize_quantity(quantity_required), unit, base_unit)

    recipe_item = RecipeItem(
        id=uuid.uuid4(),
        recipe_id=recipe.id,
        inventory_item_id=inventory_item_id,
        quantity_required=quantize_quantity(quantity_required),
        unit_id=unit_id,
        base_quantity=base_quantity,
        waste_factor=waste_factor,
        storage_location_id=storage_location_id,
        display_order=display_order,
        notes=notes,
    )
    session.add(recipe_item)
    await session.flush()
    return recipe_item


async def archive_recipe(
    session: AsyncSession, *, actor: StaffUser, recipe: Recipe, request: Request | None
) -> Recipe:
    recipe.is_active = False
    recipe.deleted_at = datetime.now(UTC)
    recipe.deleted_by = actor.id
    recipe.updated_by = actor.id
    recipe.version += 1
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.recipe.archived",
        target_type="recipe",
        target_id=recipe.id,
        request=request,
        safe_metadata={"recipe_code": recipe.recipe_code},
    )
    return recipe


# --- Costing ------------------------------------------------------------


@dataclass(frozen=True)
class IngredientCost:
    recipe_item_id: uuid.UUID
    inventory_item_id: uuid.UUID
    inventory_item_name: str
    base_quantity: Decimal
    effective_quantity: Decimal
    unit_cost_minor: int | None
    cost_minor: int | None
    cost_source: str | None  # "standard" | "latest_purchase" | None


@dataclass(frozen=True)
class RecipeCost:
    recipe_id: uuid.UUID
    ingredients: list[IngredientCost] = field(default_factory=list)
    total_ingredient_cost_minor: int | None = None
    effective_yield: Decimal = Decimal("1.000")
    cost_per_yield_minor: int | None = None
    selling_price_minor: int | None = None
    gross_margin_minor: int | None = None
    gross_margin_percentage: Decimal | None = None
    missing_cost_item_names: list[str] = field(default_factory=list)


def _round_minor(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


async def calculate_recipe_cost(session: AsyncSession, *, recipe: Recipe) -> RecipeCost:
    if not recipe.is_active:
        raise InactiveRecipeError(f"Recipe {recipe.recipe_code} is not active.")

    lines = (
        await session.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id))
    ).all()

    ingredients: list[IngredientCost] = []
    total = Decimal("0")
    missing: list[str] = []
    all_known = True

    for line in lines:
        item = await session.get(InventoryItem, line.inventory_item_id)
        assert item is not None
        waste_divisor = Decimal(1) - line.waste_factor
        effective_quantity = (
            quantize_quantity(line.base_quantity / waste_divisor)
            if waste_divisor > ZERO
            else line.base_quantity
        )

        unit_cost_minor: int | None = None
        cost_source: str | None = None
        if item.standard_cost_minor is not None:
            unit_cost_minor = item.standard_cost_minor
            cost_source = "standard"
        elif item.latest_purchase_cost_minor is not None:
            unit_cost_minor = item.latest_purchase_cost_minor
            cost_source = "latest_purchase"

        cost_minor: int | None = None
        if unit_cost_minor is not None:
            cost_minor = _round_minor(effective_quantity * Decimal(unit_cost_minor))
            total += Decimal(cost_minor)
        else:
            all_known = False
            missing.append(item.name)

        ingredients.append(
            IngredientCost(
                recipe_item_id=line.id,
                inventory_item_id=item.id,
                inventory_item_name=item.name,
                base_quantity=line.base_quantity,
                effective_quantity=effective_quantity,
                unit_cost_minor=unit_cost_minor,
                cost_minor=cost_minor,
                cost_source=cost_source,
            )
        )

    if not all_known:
        return RecipeCost(
            recipe_id=recipe.id,
            ingredients=ingredients,
            total_ingredient_cost_minor=None,
            missing_cost_item_names=missing,
        )

    loss_fraction = recipe.preparation_loss_percentage / Decimal(100)
    effective_yield = quantize_quantity(recipe.yield_quantity * (Decimal(1) - loss_fraction))
    total_int = _round_minor(total)
    cost_per_yield_minor = (
        _round_minor(Decimal(total_int) / effective_yield) if effective_yield > ZERO else None
    )

    selling_price_minor: int | None = None
    if recipe.variant_id is not None:
        variant = await session.get(ProductVariant, recipe.variant_id)
        if variant is not None:
            selling_price_minor = variant.price_minor
    else:
        product = await session.get(Product, recipe.product_id)
        if product is not None:
            selling_price_minor = product.base_price_minor

    gross_margin_minor: int | None = None
    gross_margin_percentage: Decimal | None = None
    if selling_price_minor is not None and cost_per_yield_minor is not None:
        gross_margin_minor = selling_price_minor - cost_per_yield_minor
        if selling_price_minor > 0:
            gross_margin_percentage = (
                Decimal(gross_margin_minor) / Decimal(selling_price_minor) * Decimal(100)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return RecipeCost(
        recipe_id=recipe.id,
        ingredients=ingredients,
        total_ingredient_cost_minor=total_int,
        effective_yield=effective_yield,
        cost_per_yield_minor=cost_per_yield_minor,
        selling_price_minor=selling_price_minor,
        gross_margin_minor=gross_margin_minor,
        gross_margin_percentage=gross_margin_percentage,
        missing_cost_item_names=missing,
    )
