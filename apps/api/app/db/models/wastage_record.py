import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

# Union of CORE_CRM_MODULES.md section 8.10's documented waste reasons
# (preparation_waste, overproduction, spoilage, expiry, customer_return,
# quality_failure, accidental_damage) and the categories this phase's own
# instruction names (spoilage, expiry, preparation waste, damage, quality
# rejection, staff error, other). Every value from both lists is present;
# the instruction's "damage"/"quality rejection" map onto the documented
# 'accidental_damage'/'quality_failure' rather than becoming duplicates.
WASTAGE_REASONS = (
    "preparation_waste",
    "overproduction",
    "spoilage",
    "expiry",
    "customer_return",
    "quality_failure",
    "accidental_damage",
    "staff_error",
    "other",
)


class WastageRecord(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """CORE_CRM_MODULES.md section 8.10 — recorded waste, spoilage, and
    damage.

    Append-only and posted immediately, for the same reason as
    StockAdjustment: waste is an observed fact at a point in time, not a
    document to stage. Every record writes exactly one negative `wastage`
    stock movement in the same transaction.

    `station` and `related_order_id` come from the documented capture list
    ("station", "linked order where applicable"). Photo evidence
    (CORE_CRM_MODULES.md section 8.10's "optional photo evidence") is
    deliberately not implemented: it would need the Phase 6 Storage adapter
    wired to a new bucket with its own validation and retention rules, which
    this phase's instruction does not ask for — recorded as a deferred item
    rather than a half-built upload path.
    """

    __tablename__ = "wastage_records"
    __table_args__ = (
        CheckConstraint(f"reason_category IN {WASTAGE_REASONS!r}", name="valid_reason_category"),
        CheckConstraint("quantity > 0", name="valid_quantity"),
        CheckConstraint(
            "value_impact_minor IS NULL OR value_impact_minor >= 0",
            name="valid_value_impact_minor",
        ),
        Index("ix_wastage_records_item_id", "inventory_item_id"),
        Index("ix_wastage_records_location_id", "storage_location_id"),
        Index("ix_wastage_records_batch_id", "batch_id"),
        Index("ix_wastage_records_reason_created", "reason_category", "created_at"),
        # Drives the "wastage today" / "highest-wastage items" dashboard
        # aggregates without scanning the full history.
        Index("ix_wastage_records_created_at", "created_at"),
        Index("ix_wastage_records_related_order_id", "related_order_id"),
    )

    wastage_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    storage_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_batches.id"), nullable=True
    )
    # In the item's base unit.
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    reason_category: Mapped[str] = mapped_column(String(48), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    station: Mapped[str | None] = mapped_column(String(120), nullable=True)
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True
    )
    value_impact_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    movement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock_movements.id"), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
