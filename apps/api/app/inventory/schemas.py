import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# Every inventory quantity is an exact Decimal end to end — this phase's own
# instruction: "Never use binary floating-point storage for inventory
# quantities, conversion factors or recipe quantities." JSON has no native
# decimal type, so quantities serialize as strings on the wire (accepted as
# either a string or a number on input, via Pydantic's normal Decimal
# coercion) rather than through float, which would silently reintroduce the
# exact precision loss this project explicitly forbids.
Qty = Annotated[Decimal, PlainSerializer(lambda v: str(v), return_type=str, when_used="json")]

UnitType = Literal["weight", "volume", "count"]
LocationType = Literal["kitchen", "dry_store", "chilled", "frozen", "bar", "packaging", "other"]
SupplierStatus = Literal["active", "inactive", "archived"]
BatchStatus = Literal["active", "depleted", "quarantined", "expired", "damaged"]
MovementType = Literal[
    "opening_balance",
    "purchase_receipt",
    "order_reservation",
    "reservation_release",
    "order_consumption",
    "wastage",
    "positive_adjustment",
    "negative_adjustment",
    "transfer_out",
    "transfer_in",
    "supplier_return",
    "customer_return",
    "stock_count_adjustment",
    "reversal",
]
ReceiptStatus = Literal["draft", "posted", "reversed"]
TransferStatus = Literal["draft", "posted", "reversed"]
CountStatus = Literal["draft", "in_progress", "submitted", "approved", "cancelled"]
AdjustmentDirection = Literal["increase", "decrease"]
AdjustmentReason = Literal[
    "count_difference",
    "data_correction",
    "damaged",
    "spoiled",
    "missing",
    "found",
    "unit_conversion_correction",
]
WastageReason = Literal[
    "preparation_waste",
    "overproduction",
    "spoilage",
    "expiry",
    "customer_return",
    "quality_failure",
    "accidental_damage",
    "staff_error",
    "other",
]
StockStatus = Literal[
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
]


def _validated_code(value: str) -> str:
    stripped = value.strip().lower()
    if not stripped:
        raise ValueError("Code cannot be empty.")
    if not all(c.isalnum() or c in "-_" for c in stripped):
        raise ValueError("Code may only contain letters, numbers, hyphens, and underscores.")
    return stripped


# --- Units of measure -----------------------------------------------------


class UnitCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=80)
    symbol: str = Field(min_length=1, max_length=16)
    unit_type: UnitType
    base_unit_id: uuid.UUID | None = None
    conversion_factor: Qty = Decimal(1)
    decimal_places: int = Field(default=3, ge=0, le=3)
    sort_order: int = Field(default=0, ge=0)


class UnitUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    symbol: str | None = Field(default=None, min_length=1, max_length=16)
    conversion_factor: Qty | None = None
    decimal_places: int | None = Field(default=None, ge=0, le=3)
    sort_order: int | None = None
    is_active: bool | None = None
    expected_version: int | None = None


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    symbol: str
    unit_type: UnitType
    base_unit_id: uuid.UUID | None
    conversion_factor: Qty
    decimal_places: int
    is_active: bool
    sort_order: int
    version: int


# --- Categories / locations -----------------------------------------------


class InventoryCategoryCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    sort_order: int = Field(default=0, ge=0)


class InventoryCategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    expected_version: int | None = None


class InventoryCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    version: int


class StorageLocationCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    location_type: LocationType = "other"
    allows_negative_stock: bool = False
    sort_order: int = Field(default=0, ge=0)


class StorageLocationUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    location_type: LocationType | None = None
    allows_negative_stock: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    expected_version: int | None = None


class StorageLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    location_type: LocationType
    allows_negative_stock: bool
    is_active: bool
    sort_order: int
    version: int


# --- Suppliers --------------------------------------------------------------


class SupplierCreateIn(BaseModel):
    supplier_code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=180)
    contact_person: str | None = Field(default=None, max_length=160)
    phone_e164: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = Field(default="IN", max_length=2)
    supply_categories: list[str] | None = None
    normal_lead_time_days: int | None = Field(default=None, ge=0)
    payment_terms: str | None = Field(default=None, max_length=120)
    minimum_order_value_minor: int | None = Field(default=None, ge=0)
    tax_identifier: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class SupplierUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    contact_person: str | None = None
    phone_e164: str | None = None
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    supply_categories: list[str] | None = None
    normal_lead_time_days: int | None = Field(default=None, ge=0)
    payment_terms: str | None = None
    minimum_order_value_minor: int | None = Field(default=None, ge=0)
    tax_identifier: str | None = None
    notes: str | None = None
    status: SupplierStatus | None = None
    expected_version: int | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_code: str
    name: str
    contact_person: str | None
    phone_e164: str | None
    email: str | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str
    supply_categories: list[str] | None
    normal_lead_time_days: int | None
    payment_terms: str | None
    minimum_order_value_minor: int | None
    tax_identifier: str | None
    notes: str | None
    status: SupplierStatus
    version: int


# --- Inventory items ---------------------------------------------------------


class InventoryItemCreateIn(BaseModel):
    item_code: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    category_id: uuid.UUID
    base_unit_id: uuid.UUID
    default_purchase_unit_id: uuid.UUID | None = None
    purchase_conversion_factor: Qty | None = None
    default_location_id: uuid.UUID | None = None
    preferred_supplier_id: uuid.UUID | None = None
    alternative_supplier_id: uuid.UUID | None = None
    standard_cost_minor: int | None = Field(default=None, ge=0)
    reorder_level: Qty = Decimal(0)
    reorder_quantity: Qty = Decimal(0)
    target_stock: Qty = Decimal(0)
    minimum_stock: Qty = Decimal(0)
    maximum_stock: Qty | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    shelf_life_days: int | None = Field(default=None, ge=0)
    is_perishable: bool = False
    requires_batch_tracking: bool = False
    requires_expiry_tracking: bool = False
    allergen_flags: list[str] | None = None
    brand: str | None = None
    supplier_item_code: str | None = None
    barcode: str | None = None
    storage_instructions: str | None = None
    notes: str | None = None


class InventoryItemUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    category_id: uuid.UUID | None = None
    default_purchase_unit_id: uuid.UUID | None = None
    purchase_conversion_factor: Qty | None = None
    default_location_id: uuid.UUID | None = None
    preferred_supplier_id: uuid.UUID | None = None
    alternative_supplier_id: uuid.UUID | None = None
    standard_cost_minor: int | None = Field(default=None, ge=0)
    reorder_level: Qty | None = None
    reorder_quantity: Qty | None = None
    target_stock: Qty | None = None
    minimum_stock: Qty | None = None
    maximum_stock: Qty | None = None
    lead_time_days: int | None = None
    shelf_life_days: int | None = None
    is_perishable: bool | None = None
    allergen_flags: list[str] | None = None
    brand: str | None = None
    supplier_item_code: str | None = None
    barcode: str | None = None
    storage_instructions: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    expected_version: int | None = None


class InventoryItemListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_code: str
    name: str
    category_id: uuid.UUID
    current_stock: Qty
    reserved_stock: Qty
    reorder_level: Qty
    stock_status: StockStatus
    preferred_supplier_id: uuid.UUID | None
    is_active: bool
    is_perishable: bool
    requires_batch_tracking: bool
    requires_expiry_tracking: bool


class InventoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_code: str
    name: str
    description: str | None
    category_id: uuid.UUID
    base_unit_id: uuid.UUID
    default_purchase_unit_id: uuid.UUID | None
    purchase_conversion_factor: Qty | None
    default_location_id: uuid.UUID | None
    preferred_supplier_id: uuid.UUID | None
    alternative_supplier_id: uuid.UUID | None
    current_stock: Qty
    reserved_stock: Qty
    reorder_level: Qty
    reorder_quantity: Qty
    target_stock: Qty
    minimum_stock: Qty
    maximum_stock: Qty | None
    standard_cost_minor: int | None
    latest_purchase_cost_minor: int | None
    average_unit_cost_minor: int | None
    lead_time_days: int | None
    shelf_life_days: int | None
    is_perishable: bool
    requires_batch_tracking: bool
    requires_expiry_tracking: bool
    allergen_flags: list[str] | None
    brand: str | None
    supplier_item_code: str | None
    barcode: str | None
    storage_instructions: str | None
    notes: str | None
    stock_status: StockStatus
    is_active: bool
    last_counted_at: datetime | None
    last_received_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class StockBalanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_item_id: uuid.UUID
    storage_location_id: uuid.UUID
    batch_id: uuid.UUID | None
    on_hand_quantity: Qty
    reserved_quantity: Qty
    last_movement_at: datetime | None
    last_counted_at: datetime | None


class InventoryBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_item_id: uuid.UUID
    batch_code: str
    storage_location_id: uuid.UUID
    supplier_id: uuid.UUID | None
    received_quantity: Qty
    remaining_quantity: Qty
    received_at: datetime
    manufactured_at: date | None
    expires_at: date | None
    unit_cost_minor: int | None
    status: BatchStatus


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    movement_number: str
    inventory_item_id: uuid.UUID
    storage_location_id: uuid.UUID
    batch_id: uuid.UUID | None
    movement_type: MovementType
    quantity_delta: Qty
    affects_on_hand: bool
    unit_cost_minor: int | None
    total_value_minor: int | None
    reference_type: str | None
    reference_id: uuid.UUID | None
    source_movement_id: uuid.UUID | None
    reversed_by_movement_id: uuid.UUID | None
    reversed_at: datetime | None
    reason: str | None
    performed_by: uuid.UUID | None
    occurred_at: datetime
    created_at: datetime


# --- Receipts -----------------------------------------------------------------


class ReceiptCreateIn(BaseModel):
    supplier_id: uuid.UUID
    storage_location_id: uuid.UUID
    received_date: date
    supplier_reference: str | None = None
    notes: str | None = None


class ReceiptItemCreateIn(BaseModel):
    inventory_item_id: uuid.UUID
    purchase_unit_id: uuid.UUID
    received_quantity: Qty
    accepted_quantity: Qty
    rejected_quantity: Qty = Decimal(0)
    unit_cost_minor: int = Field(ge=0)
    batch_code: str | None = None
    manufactured_at: date | None = None
    expires_at: date | None = None
    notes: str | None = None


class ReceiptReverseIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ReceiptItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    receipt_id: uuid.UUID
    inventory_item_id: uuid.UUID
    purchase_unit_id: uuid.UUID
    received_quantity: Qty
    accepted_quantity: Qty
    rejected_quantity: Qty
    base_quantity: Qty
    unit_cost_minor: int
    line_total_minor: int
    batch_code: str | None
    manufactured_at: date | None
    expires_at: date | None
    batch_id: uuid.UUID | None
    notes: str | None


class ReceiptListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    receipt_number: str
    supplier_id: uuid.UUID
    storage_location_id: uuid.UUID
    received_date: date
    status: ReceiptStatus
    total_value_minor: int
    created_at: datetime


class ReceiptOut(ReceiptListItemOut):
    supplier_reference: str | None
    notes: str | None
    posted_by: uuid.UUID | None
    posted_at: datetime | None
    reversed_by: uuid.UUID | None
    reversed_at: datetime | None
    reversal_reason: str | None
    version: int
    items: list[ReceiptItemOut] = Field(default_factory=list)


# --- Adjustments / wastage ----------------------------------------------------


class AdjustmentCreateIn(BaseModel):
    inventory_item_id: uuid.UUID
    storage_location_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    direction: AdjustmentDirection
    quantity: Qty
    reason_category: AdjustmentReason
    reason: str = Field(min_length=1, max_length=500)
    approved_by: uuid.UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=160)


class AdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    adjustment_number: str
    inventory_item_id: uuid.UUID
    storage_location_id: uuid.UUID
    batch_id: uuid.UUID | None
    direction: AdjustmentDirection
    quantity: Qty
    reason_category: AdjustmentReason
    reason: str
    value_impact_minor: int | None
    movement_id: uuid.UUID
    recorded_by: uuid.UUID
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime


class WastageCreateIn(BaseModel):
    inventory_item_id: uuid.UUID
    storage_location_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    quantity: Qty
    reason_category: WastageReason
    reason: str = Field(min_length=1, max_length=500)
    station: str | None = Field(default=None, max_length=120)
    related_order_id: uuid.UUID | None = None
    approved_by: uuid.UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=160)


class WastageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    wastage_number: str
    inventory_item_id: uuid.UUID
    storage_location_id: uuid.UUID
    batch_id: uuid.UUID | None
    quantity: Qty
    reason_category: WastageReason
    reason: str
    station: str | None
    related_order_id: uuid.UUID | None
    value_impact_minor: int | None
    movement_id: uuid.UUID
    recorded_by: uuid.UUID
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime


# --- Transfers -----------------------------------------------------------------


class TransferCreateIn(BaseModel):
    source_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    notes: str | None = None


class TransferItemCreateIn(BaseModel):
    inventory_item_id: uuid.UUID
    batch_id: uuid.UUID | None = None
    quantity: Qty
    notes: str | None = None


class TransferReverseIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class TransferItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transfer_id: uuid.UUID
    inventory_item_id: uuid.UUID
    batch_id: uuid.UUID | None
    destination_batch_id: uuid.UUID | None
    quantity: Qty
    notes: str | None


class TransferListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transfer_number: str
    source_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    status: TransferStatus
    created_at: datetime


class TransferOut(TransferListItemOut):
    notes: str | None
    requested_by: uuid.UUID
    posted_by: uuid.UUID | None
    posted_at: datetime | None
    reversed_by: uuid.UUID | None
    reversed_at: datetime | None
    reversal_reason: str | None
    version: int
    items: list[TransferItemOut] = Field(default_factory=list)


# --- Stock counts --------------------------------------------------------------


class StockCountCreateIn(BaseModel):
    storage_location_id: uuid.UUID
    scheduled_date: date | None = None
    notes: str | None = None


class StockCountLineRecordIn(BaseModel):
    counted_quantity: Qty
    reason: str | None = None
    notes: str | None = None


class StockCountLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    count_id: uuid.UUID
    inventory_item_id: uuid.UUID
    batch_id: uuid.UUID | None
    system_quantity: Qty
    counted_quantity: Qty | None
    variance_quantity: Qty | None
    variance_value_minor: int | None
    reason: str | None
    notes: str | None


class StockCountListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    count_number: str
    storage_location_id: uuid.UUID
    status: CountStatus
    scheduled_date: date | None
    created_at: datetime


class StockCountOut(StockCountListItemOut):
    started_at: datetime | None
    completed_at: datetime | None
    counted_by: uuid.UUID | None
    submitted_by: uuid.UUID | None
    submitted_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    cancelled_at: datetime | None
    notes: str | None
    version: int
    lines: list[StockCountLineOut] = Field(default_factory=list)


# --- Recipes --------------------------------------------------------------------


class RecipeItemCreateIn(BaseModel):
    inventory_item_id: uuid.UUID
    quantity_required: Qty
    unit_id: uuid.UUID
    waste_factor: Qty = Decimal(0)
    storage_location_id: uuid.UUID | None = None
    display_order: int = Field(default=0, ge=0)
    notes: str | None = None


class RecipeCreateIn(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    yield_quantity: Qty = Decimal(1)
    yield_unit_id: uuid.UUID | None = None
    preparation_loss_percentage: Qty = Decimal(0)
    effective_from: datetime | None = None
    notes: str | None = None
    items: list[RecipeItemCreateIn] = Field(default_factory=list)


class RecipeItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipe_id: uuid.UUID
    inventory_item_id: uuid.UUID
    quantity_required: Qty
    unit_id: uuid.UUID
    base_quantity: Qty
    waste_factor: Qty
    storage_location_id: uuid.UUID | None
    display_order: int
    notes: str | None


class RecipeListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipe_code: str
    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    yield_quantity: Qty
    is_active: bool
    effective_from: datetime
    effective_to: datetime | None


class RecipeOut(RecipeListItemOut):
    yield_unit_id: uuid.UUID | None
    preparation_loss_percentage: Qty
    notes: str | None
    version: int
    items: list[RecipeItemOut] = Field(default_factory=list)


class IngredientCostOut(BaseModel):
    recipe_item_id: uuid.UUID
    inventory_item_id: uuid.UUID
    inventory_item_name: str
    base_quantity: Qty
    effective_quantity: Qty
    unit_cost_minor: int | None
    cost_minor: int | None
    cost_source: str | None


class RecipeCostOut(BaseModel):
    recipe_id: uuid.UUID
    ingredients: list[IngredientCostOut]
    total_ingredient_cost_minor: int | None
    effective_yield: Qty
    cost_per_yield_minor: int | None
    selling_price_minor: int | None
    gross_margin_minor: int | None
    gross_margin_percentage: Decimal | None
    missing_cost_item_names: list[str]


# --- Balance verification --------------------------------------------------------


class BalanceDriftOut(BaseModel):
    inventory_item_id: uuid.UUID
    storage_location_id: uuid.UUID
    batch_id: uuid.UUID | None
    projected_on_hand: Qty
    ledger_on_hand: Qty
    difference: Qty


class BalanceRebuildResultOut(BaseModel):
    coordinates: int
    created: int
    updated: int


# --- Dashboard --------------------------------------------------------------------


class InventoryDashboardStatsOut(BaseModel):
    total_active_items: int
    total_stock_value_minor: int
    low_stock_count: int
    critical_stock_count: int
    out_of_stock_count: int
    expiring_batches_7d: int
    expired_batches: int
    wastage_today_count: int
    wastage_today_value_minor: int
    receipts_today_count: int
    transfers_in_progress: int
    pending_stock_counts: int
