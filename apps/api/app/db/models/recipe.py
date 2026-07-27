import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Recipe(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 9.4, CORE_CRM_MODULES.md section 7.9.

    **Recipe resolution policy** (this phase's own instruction: "If the
    documentation does not define inheritance, use one explicit resolved
    recipe per sellable product/variant and document the decision" — no
    canonical document defines variant inheritance):

      1. An exact `(product_id, variant_id)` match wins.
      2. Otherwise the product's base recipe `(product_id, variant_id IS
         NULL)` applies.

    There is no merging, extending, or overriding of individual ingredients
    between the two. A variant recipe is a complete, standalone ingredient
    list. This keeps "what will be consumed" a single unambiguous lookup
    with no partial-inheritance surprises, which matters because the answer
    directly drives irreversible stock deductions. Recorded in
    DATABASE_AND_API.md section 9.8.

    `version` is the documented column and is bumped on every edit, doubling
    as the optimistic-concurrency token (matching how Phase 5-7 use
    AuditedMixin.version). `effective_from`/`effective_to` come from the
    documented schema; the resolver only considers a recipe whose window
    contains the processing time, so a scheduled recipe change cannot
    retroactively alter what an already-processed order consumed.
    """

    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint("yield_quantity > 0", name="valid_yield_quantity"),
        CheckConstraint(
            "preparation_loss_percentage >= 0 AND preparation_loss_percentage < 100",
            name="valid_preparation_loss_percentage",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="effective_window_ordered",
        ),
        Index("ix_recipes_product_id", "product_id"),
        Index("ix_recipes_variant_id", "variant_id"),
        # At most one *active* recipe per product (base) and per
        # product+variant. Two partial unique indexes because PostgreSQL
        # treats NULLs as distinct in a UNIQUE constraint, which would
        # otherwise allow several competing base recipes for one product and
        # make resolution non-deterministic.
        Index(
            "uq_recipes_active_variant",
            "product_id",
            "variant_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND is_active AND variant_id IS NOT NULL"),
        ),
        Index(
            "uq_recipes_active_base",
            "product_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND is_active AND variant_id IS NULL"),
        ),
    )

    recipe_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id"), nullable=True
    )
    # How many sellable units one execution of this recipe produces. Almost
    # always 1 for a plated fast-food item, but batch-prepared components
    # (a 20-litre sauce batch) need a real yield to cost correctly.
    yield_quantity: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(1)
    )
    yield_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units_of_measure.id"), nullable=True
    )
    # CORE_CRM_MODULES.md section 7.10's preparation-loss concept, applied to
    # the whole recipe. Per-ingredient loss is the documented
    # `recipe_items.waste_factor`; this is the additional loss on the
    # finished output (e.g. reduction during cooking).
    preparation_loss_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal(0)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecipeItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DATABASE_AND_API.md section 9.5.

    The documented schema specifies a composite primary key on
    `(recipe_id, inventory_item_id)`. A surrogate `id` with a UNIQUE
    constraint on that pair is used instead, for consistency with every
    other line-item table in this project (`order_items`,
    `stock_receipt_items`, …) and because `display_order` needs a stable row
    identity to reorder against. The uniqueness guarantee the documented PK
    provided is preserved exactly by `uq_recipe_items_recipe_item`.

    `base_quantity` is `quantity_required` converted into the inventory
    item's base unit and frozen at write time — the ledger and costing both
    read it directly, so a later correction to a unit's conversion factor
    cannot silently change what historical recipes meant.
    """

    __tablename__ = "recipe_items"
    __table_args__ = (
        CheckConstraint("quantity_required > 0", name="valid_quantity_required"),
        CheckConstraint("base_quantity > 0", name="valid_base_quantity"),
        CheckConstraint("waste_factor >= 0 AND waste_factor < 1", name="valid_waste_factor"),
        CheckConstraint("display_order >= 0", name="valid_display_order"),
        Index(
            "uq_recipe_items_recipe_item",
            "recipe_id",
            "inventory_item_id",
            unique=True,
        ),
        Index("ix_recipe_items_recipe_id", "recipe_id"),
        # Powers the "recipes using this item" tab and the low-stock
        # dependency filter (which menu products are at risk).
        Index("ix_recipe_items_inventory_item_id", "inventory_item_id"),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    quantity_required: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units_of_measure.id"), nullable=False)
    base_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    # DATABASE_AND_API.md section 9.5's documented NUMERIC(8,4) fraction
    # (0.05 == 5% expected trim/spillage loss on this ingredient).
    waste_factor: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal(0))
    # Lets a specific ingredient be drawn from somewhere other than the
    # item's default location (e.g. a bar recipe pulling from the Bar rather
    # than the Main Kitchen). NULL means "use the item's default location".
    storage_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
