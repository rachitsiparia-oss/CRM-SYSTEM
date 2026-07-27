import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    BigInteger,
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

# DATABASE_AND_API.md section 9.1's documented closed list, identical to
# CORE_CRM_MODULES.md section 8.3 and PROJECT_PLAN.md section 8.3.
#
# Only a subset is reachable through Phase 8 service code:
# in_stock/low_stock/critical_stock/out_of_stock are *derived* from live
# balances against reorder levels (see app.inventory.status), while
# quarantined/expired/damaged/under_count_review/discontinued are
# *operator-set* states. 'reserved' is deliberately never assigned: reserved
# quantity is a number on the balance projection, not a whole-item state —
# an item with some stock reserved and some available is simultaneously
# "reserved" and sellable, so collapsing that into one status would lose
# information the balance columns already carry precisely.
STOCK_STATUSES = (
    "in_stock",
    "low_stock",
    "critical_stock",
    "out_of_stock",
    "reserved",
    "quarantined",
    "expired",
    "damaged",
    "under_count_review",
    "discontinued",
)

# Statuses this phase's own code derives from live balances. Anything else
# is operator-owned and must not be overwritten by the derivation pass.
DERIVED_STOCK_STATUSES = ("in_stock", "low_stock", "critical_stock", "out_of_stock")


class InventoryItem(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 9.1, CORE_CRM_MODULES.md sections 8.2/8.5.

    An inventory item is a stock-controlled ingredient or operational
    material. It is never a sellable menu product — this phase's own
    instruction is explicit ("Do not combine menu products and inventory
    items"), and the two are linked only through `recipes`/`recipe_items`.

    `category`/`storage_zone`/`unit_of_measure` are documented in section
    9.1 as VARCHAR columns; they are foreign keys here
    (`category_id`/`default_location_id`/`base_unit_id`) because this
    phase's own instruction requires managed unit conversion, per-location
    balances, and manageable categories. See DATABASE_AND_API.md section
    9.8 for the recorded deviation.

    `current_stock`/`reserved_stock` (both documented in section 9.1) are
    kept as *denormalized roll-ups across all locations*, maintained
    transactionally alongside `stock_balances` — which is the real
    per-location/per-batch projection this phase requires. Neither is a
    source of truth: `stock_movements` is (this phase's own instruction,
    "Stock Ledger Is the Source of Truth"), and both are rebuildable from
    it. The same summary-column-plus-detail-table pattern Phase 6 used for
    `products.image_storage_path` and Phase 7 used for
    `orders.discount_minor`.
    """

    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint(f"stock_status IN {STOCK_STATUSES!r}", name="valid_stock_status"),
        CheckConstraint("reorder_level >= 0", name="valid_reorder_level"),
        CheckConstraint("target_stock >= 0", name="valid_target_stock"),
        CheckConstraint("reorder_quantity >= 0", name="valid_reorder_quantity"),
        CheckConstraint("minimum_stock >= 0", name="valid_minimum_stock"),
        CheckConstraint("maximum_stock IS NULL OR maximum_stock >= 0", name="valid_maximum_stock"),
        CheckConstraint(
            "standard_cost_minor IS NULL OR standard_cost_minor >= 0",
            name="valid_standard_cost_minor",
        ),
        CheckConstraint(
            "latest_purchase_cost_minor IS NULL OR latest_purchase_cost_minor >= 0",
            name="valid_latest_purchase_cost_minor",
        ),
        CheckConstraint(
            "average_unit_cost_minor IS NULL OR average_unit_cost_minor >= 0",
            name="valid_average_unit_cost_minor",
        ),
        CheckConstraint(
            "purchase_conversion_factor IS NULL OR purchase_conversion_factor > 0",
            name="valid_purchase_conversion_factor",
        ),
        CheckConstraint(
            "lead_time_days IS NULL OR lead_time_days >= 0", name="valid_lead_time_days"
        ),
        CheckConstraint(
            "shelf_life_days IS NULL OR shelf_life_days >= 0", name="valid_shelf_life_days"
        ),
        # An expiry-tracked item must also be batch-tracked: expiry is a
        # property of a specific received batch, so there is nowhere to
        # record it otherwise.
        CheckConstraint(
            "NOT requires_expiry_tracking OR requires_batch_tracking",
            name="expiry_tracking_requires_batch_tracking",
        ),
        Index("ix_inventory_items_category_id", "category_id"),
        Index("ix_inventory_items_preferred_supplier_id", "preferred_supplier_id"),
        Index("ix_inventory_items_name", "name"),
        Index("ix_inventory_items_stock_status", "stock_status"),
        Index(
            "ix_inventory_items_active",
            "category_id",
            "name",
            postgresql_where=text("deleted_at IS NULL AND is_active"),
        ),
        # Supports the low-stock/reorder dashboard query without scanning
        # the whole table (this phase's own requirement that low-stock
        # calculations use real database quantities).
        Index(
            "ix_inventory_items_reorder_watch",
            "stock_status",
            "current_stock",
            postgresql_where=text("deleted_at IS NULL AND is_active"),
        ),
        Index(
            "uq_inventory_items_barcode",
            "barcode",
            unique=True,
            postgresql_where=text("barcode IS NOT NULL"),
        ),
    )

    item_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_categories.id"), nullable=False
    )
    # The unit every ledger quantity for this item is expressed in. All
    # movements, balances, and recipe quantities are stored converted into
    # this unit so arithmetic never needs a conversion at read time.
    base_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units_of_measure.id"), nullable=False
    )
    # The unit this item is normally *purchased* in (e.g. buy a "box" of
    # 24, stock in "pieces"). `purchase_conversion_factor` is how many base
    # units one purchase unit yields, and is only needed when the purchase
    # unit is not itself convertible through units_of_measure (e.g. a
    # supplier-specific box size).
    default_purchase_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units_of_measure.id"), nullable=True
    )
    purchase_conversion_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    default_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True
    )
    preferred_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True
    )
    alternative_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True
    )

    # --- Denormalized roll-ups, never a source of truth (see class docstring)
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )
    reserved_stock: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )

    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )
    # This phase's own "reorder quantity" field — how much to buy when the
    # reorder level is hit. Distinct from `target_stock` (documented in
    # section 9.1), which is the level to replenish *up to*.
    reorder_quantity: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )
    target_stock: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )
    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )
    maximum_stock: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True)

    # --- Costing (all integer minor units per base unit, CLAUDE.md section 7)
    # `standard_cost_minor` is the recipe-costing basis (see
    # app.inventory.costing and DATABASE_AND_API.md section 9.8's costing
    # policy). The other two are maintained from receipt postings for
    # reporting and variance visibility.
    standard_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    latest_purchase_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    average_unit_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shelf_life_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_perishable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_batch_tracking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_expiry_tracking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allergen_flags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # Optional operational fields from this phase's own instruction.
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    supplier_item_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    stock_status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_stock")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
