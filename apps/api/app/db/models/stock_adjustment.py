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

ADJUSTMENT_DIRECTIONS = ("increase", "decrease")

# CORE_CRM_MODULES.md section 8.9's documented closed list.
ADJUSTMENT_REASONS = (
    "count_difference",
    "data_correction",
    "damaged",
    "spoiled",
    "missing",
    "found",
    "unit_conversion_correction",
)


class StockAdjustment(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """CORE_CRM_MODULES.md section 8.9 — a manual stock correction.

    Append-only: an adjustment record is written once, at the moment it is
    posted, together with its ledger movement in the same transaction. There
    is no draft state (unlike receipts/transfers/counts) because an
    adjustment is a single-line instantaneous correction with nothing to
    stage — this phase's own instruction lists no statuses for it, only
    required fields plus "approval where required by permission policy".

    `approved_by` records who authorized a sensitive adjustment. It is
    enforced at the service layer against `inventory.adjustments.approve`
    rather than by a NOT NULL constraint, so the approval requirement can
    follow permission policy without making every adjustment blocked on a
    second person.
    """

    __tablename__ = "stock_adjustments"
    __table_args__ = (
        CheckConstraint(f"direction IN {ADJUSTMENT_DIRECTIONS!r}", name="valid_direction"),
        CheckConstraint(f"reason_category IN {ADJUSTMENT_REASONS!r}", name="valid_reason_category"),
        # Always a positive magnitude; `direction` carries the sign so a
        # negative quantity paired with 'decrease' can never double-negate.
        CheckConstraint("quantity > 0", name="valid_quantity"),
        Index("ix_stock_adjustments_item_id", "inventory_item_id"),
        Index("ix_stock_adjustments_location_id", "storage_location_id"),
        Index("ix_stock_adjustments_created_at", "created_at"),
    )

    adjustment_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    storage_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_batches.id"), nullable=True
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    # In the item's base unit, converted server-side from whatever unit the
    # operator entered (preserved on the paired stock_movement row).
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    reason_category: Mapped[str] = mapped_column(String(48), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    value_impact_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    movement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock_movements.id"), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
