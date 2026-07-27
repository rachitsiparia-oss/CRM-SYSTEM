import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

TRANSFER_STATUSES = ("draft", "posted", "reversed")


class StockTransfer(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """An internal transfer of stock between two storage locations inside the
    single RKPR restaurant — never between branches (CLAUDE.md section 24).

    Posting is atomic and always creates BOTH halves: a `transfer_out`
    movement at the source and a `transfer_in` movement at the destination,
    linked by `stock_movements.source_movement_id`. This phase's own
    instruction is explicit: "Never create only one side of a transfer."
    """

    __tablename__ = "stock_transfers"
    __table_args__ = (
        CheckConstraint(f"status IN {TRANSFER_STATUSES!r}", name="valid_status"),
        # This phase's own rule: "Source and destination locations cannot be
        # the same." Enforced in the database, not only in service code.
        CheckConstraint(
            "source_location_id <> destination_location_id",
            name="source_and_destination_differ",
        ),
        Index("ix_stock_transfers_source_location_id", "source_location_id"),
        Index("ix_stock_transfers_destination_location_id", "destination_location_id"),
        Index("ix_stock_transfers_status_created", "status", "created_at"),
    )

    transfer_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    source_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    destination_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    posted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class StockTransferItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One line of a transfer.

    `destination_batch_id` is set at post time when the transferred stock is
    batch-tracked: moving a batch between locations creates a *new* batch row
    at the destination carrying the same code, expiry, and unit cost, because
    `inventory_batches.storage_location_id` pins a batch to one location.
    Both batch rows share the same `batch_code`, so traceability back to the
    original supplier delivery survives the move.
    """

    __tablename__ = "stock_transfer_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="valid_quantity"),
        Index("ix_stock_transfer_items_transfer_id", "transfer_id"),
        Index("ix_stock_transfer_items_item_id", "inventory_item_id"),
    )

    transfer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock_transfers.id"), nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_batches.id"), nullable=True
    )
    destination_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_batches.id"), nullable=True
    )
    # In the item's base unit; the entered unit is preserved on the paired
    # movement rows.
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
