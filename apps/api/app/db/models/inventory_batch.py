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
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# Not enumerated by DATABASE_AND_API.md section 9.2 (`status VARCHAR(32) NOT
# NULL` only). These mirror the batch-relevant subset of the documented
# item-level stock statuses (CORE_CRM_MODULES.md section 8.3) plus
# 'depleted', which a batch needs and an item does not.
BATCH_STATUSES = ("active", "depleted", "quarantined", "expired", "damaged")


class InventoryBatch(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """DATABASE_AND_API.md section 9.2, CORE_CRM_MODULES.md section 8.12.

    Only created for items with `requires_batch_tracking` or
    `requires_expiry_tracking` — this phase's own instruction is explicit
    ("Do not require batches for items that are not batch-tracked").

    `remaining_quantity` is a projection maintained transactionally with the
    ledger, exactly like `stock_balances`; `stock_movements` filtered by
    `batch_id` remains the source of truth and can rebuild it.

    `storage_location_id` is added beyond the documented column list: a
    batch physically sits in one location, and transfers move specific
    batches between locations, so the location cannot live only on the
    parent item.
    """

    __tablename__ = "inventory_batches"
    __table_args__ = (
        # DATABASE_AND_API.md section 9.2's documented "unique item and
        # batch code".
        UniqueConstraint("inventory_item_id", "batch_code", name="uq_inventory_batches_item_code"),
        CheckConstraint(f"status IN {BATCH_STATUSES!r}", name="valid_status"),
        CheckConstraint("received_quantity > 0", name="valid_received_quantity"),
        CheckConstraint("remaining_quantity >= 0", name="valid_remaining_quantity"),
        CheckConstraint(
            "remaining_quantity <= received_quantity", name="remaining_not_above_received"
        ),
        CheckConstraint(
            "unit_cost_minor IS NULL OR unit_cost_minor >= 0", name="valid_unit_cost_minor"
        ),
        # CORE_CRM_MODULES.md section 8.20's "batch expires before receipt
        # date" edge case, enforced in the database rather than only in
        # service code.
        CheckConstraint(
            "expires_at IS NULL OR expires_at >= received_at::date",
            name="expiry_not_before_received",
        ),
        CheckConstraint(
            "expires_at IS NULL OR manufactured_at IS NULL OR expires_at >= manufactured_at",
            name="expiry_not_before_manufactured",
        ),
        Index("ix_inventory_batches_item_id", "inventory_item_id"),
        Index("ix_inventory_batches_location_id", "storage_location_id"),
        Index("ix_inventory_batches_supplier_id", "supplier_id"),
        # Drives both the FEFO allocation order and the expiring/expired
        # dashboard views over only the batches that still hold stock.
        Index(
            "ix_inventory_batches_fefo",
            "inventory_item_id",
            "expires_at",
            "received_at",
            postgresql_where=text("status = 'active' AND remaining_quantity > 0"),
        ),
        Index(
            "ix_inventory_batches_expiring",
            "expires_at",
            postgresql_where=text(
                "expires_at IS NOT NULL AND status = 'active' AND remaining_quantity > 0"
            ),
        ),
    )

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    batch_code: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    manufactured_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    unit_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
