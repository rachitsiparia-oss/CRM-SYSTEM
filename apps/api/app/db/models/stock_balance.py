import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StockBalance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The performant balance projection this phase requires, keyed on
    `inventory item + storage location + optional batch`.

    Not a source of truth. Per this phase's own instruction it:
      - is updated transactionally with every ledger movement (same
        `session.flush()`, same transaction — never a background sync),
      - is fully rebuildable from `stock_movements` alone
        (`app.inventory.balances.rebuild_balances`),
      - never becomes an independent authority.

    `available_quantity` is deliberately NOT stored: it is defined by this
    phase's instruction as exactly `on_hand - reserved`, so storing it would
    create a third number that can disagree with the other two. It is
    computed on read (and in SQL where a query needs to filter on it).

    A NULL `batch_id` row is the balance for the item's non-batch-tracked
    stock at that location; batch-tracked items carry one row per batch.
    Both shapes coexist because `requires_batch_tracking` is per item.
    """

    __tablename__ = "stock_balances"
    __table_args__ = (
        CheckConstraint("on_hand_quantity >= 0 OR allows_negative", name="valid_on_hand_quantity"),
        CheckConstraint("reserved_quantity >= 0", name="valid_reserved_quantity"),
        # This phase's own rule: "Never allow reserved quantity to exceed
        # on-hand quantity unless explicitly permitted by documented
        # policy." The permitted case is a location with
        # allows_negative_stock, which `allows_negative` mirrors so the
        # constraint can be enforced without a cross-table subquery.
        CheckConstraint(
            "reserved_quantity <= on_hand_quantity OR allows_negative",
            name="reserved_not_above_on_hand",
        ),
        # One balance row per item+location+batch. Two partial unique
        # indexes rather than one constraint, because in PostgreSQL a UNIQUE
        # constraint treats NULLs as distinct — which would silently permit
        # duplicate non-batch rows for the same item+location.
        Index(
            "uq_stock_balances_item_location_batch",
            "inventory_item_id",
            "storage_location_id",
            "batch_id",
            unique=True,
            postgresql_where=text("batch_id IS NOT NULL"),
        ),
        Index(
            "uq_stock_balances_item_location_nobatch",
            "inventory_item_id",
            "storage_location_id",
            unique=True,
            postgresql_where=text("batch_id IS NULL"),
        ),
        Index("ix_stock_balances_item_id", "inventory_item_id"),
        Index("ix_stock_balances_location_id", "storage_location_id"),
        Index("ix_stock_balances_batch_id", "batch_id"),
        # Supports the "which locations actually hold this item" and
        # allocation-candidate queries without scanning empty rows.
        Index(
            "ix_stock_balances_with_stock",
            "inventory_item_id",
            "storage_location_id",
            postgresql_where=text("on_hand_quantity > 0"),
        ),
    )

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    storage_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_batches.id"), nullable=True
    )
    on_hand_quantity: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )
    reserved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(16, 3), nullable=False, default=Decimal(0)
    )
    # Mirrors storage_locations.allows_negative_stock at write time so the
    # CHECK constraints above can be enforced row-locally. Kept in sync by
    # app.inventory.balances whenever a balance row is created or the
    # location policy changes.
    allows_negative: Mapped[bool] = mapped_column(nullable=False, default=False)
    last_movement_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
