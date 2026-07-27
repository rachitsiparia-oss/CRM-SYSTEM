import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# This phase's own instruction: "Statuses: draft, posted, reversed."
# A draft is editable; posting is the one-way transition that writes the
# ledger; reversal is the only correction path (this phase's "No Destructive
# Ledger Editing" rule).
RECEIPT_STATUSES = ("draft", "posted", "reversed")


class StockReceipt(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Operational goods-receipt recording — DATABASE_AND_API.md section 9.7
    (`goods_receipts`), CORE_CRM_MODULES.md section 8.8.

    Standalone: there is no `purchase_order_id`. DATABASE_AND_API.md section
    9.7 also names `purchase_orders`/`purchase_order_items` and
    CORE_CRM_MODULES.md section 8.15 documents PO statuses, but this phase's
    own 15-area implementation scope does not include purchase orders, and
    its DO-NOT-BUILD list explicitly guards the PO approval workflow. A
    receipt therefore references a supplier plus a free-text
    `supplier_reference` (invoice/delivery-note number) — enough to record
    what physically arrived. See DATABASE_AND_API.md section 9.8 for the
    recorded deferral.

    Supplier invoice settlement is explicitly out of scope for this phase,
    so there are no payable, tax, or settlement columns.
    """

    __tablename__ = "stock_receipts"
    __table_args__ = (
        CheckConstraint(f"status IN {RECEIPT_STATUSES!r}", name="valid_status"),
        CheckConstraint("total_value_minor >= 0", name="valid_total_value_minor"),
        Index("ix_stock_receipts_supplier_id", "supplier_id"),
        Index("ix_stock_receipts_status_received", "status", "received_date"),
        Index("ix_stock_receipts_location_id", "storage_location_id"),
    )

    receipt_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    storage_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    # Rolled up from the receipt's accepted line totals when it is posted.
    total_value_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class StockReceiptItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DATABASE_AND_API.md section 9.7 (`goods_receipt_items`).

    `received_quantity` is what the delivery note claimed;
    `accepted_quantity` is what was actually taken into stock and is the
    only figure that reaches the ledger. `rejected_quantity` is recorded for
    supplier-quality visibility (CORE_CRM_MODULES.md section 8.8 step 7,
    "record damaged or rejected quantity") but deliberately creates no stock
    movement — rejected goods never entered inventory, so posting a
    movement for them would be recording stock the restaurant does not have.
    """

    __tablename__ = "stock_receipt_items"
    __table_args__ = (
        CheckConstraint("received_quantity > 0", name="valid_received_quantity"),
        CheckConstraint("accepted_quantity >= 0", name="valid_accepted_quantity"),
        CheckConstraint("rejected_quantity >= 0", name="valid_rejected_quantity"),
        CheckConstraint(
            "accepted_quantity + rejected_quantity <= received_quantity",
            name="accepted_plus_rejected_within_received",
        ),
        CheckConstraint("base_quantity >= 0", name="valid_base_quantity"),
        CheckConstraint("unit_cost_minor >= 0", name="valid_unit_cost_minor"),
        CheckConstraint("line_total_minor >= 0", name="valid_line_total_minor"),
        Index("ix_stock_receipt_items_receipt_id", "receipt_id"),
        Index("ix_stock_receipt_items_item_id", "inventory_item_id"),
    )

    receipt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock_receipts.id"), nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    # The unit the goods were purchased/delivered in, which may differ from
    # the item's base unit.
    purchase_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("units_of_measure.id"), nullable=False
    )
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    accepted_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    rejected_quantity: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )
    # `accepted_quantity` converted into the item's base unit — computed
    # server-side at post time and frozen, so the ledger effect stays
    # reproducible even if a unit's conversion factor is later corrected.
    base_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    # Cost per *purchase* unit, as invoiced. The per-base-unit cost the
    # ledger and item costing use is derived from this and `base_quantity`.
    unit_cost_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Batch details, required when the item is batch- or expiry-tracked.
    batch_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    manufactured_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Set at post time to the batch this line created, so a reversal knows
    # exactly which batch to unwind.
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_batches.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
