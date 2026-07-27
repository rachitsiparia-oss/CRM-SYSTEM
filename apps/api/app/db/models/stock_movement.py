import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

# The canonical movement-type set for this phase.
#
# DATABASE_AND_API.md section 9.3 requires types "including purchase
# receipt, kitchen issue, recipe consumption, adjustment, waste, damage,
# expiry, return, transfer, count correction, reservation, and release"
# (CORE_CRM_MODULES.md section 8.7 and PROJECT_PLAN.md section 8.4 list the
# same set in prose). This phase's own instruction gives a more precise
# list that splits several of those into directional pairs. Both are
# honoured: every documented concept has exactly one code here, with
# transfer/adjustment split by direction so the sign is never ambiguous.
#
# Mapping from the documented prose names:
#   purchase receipt      -> purchase_receipt
#   kitchen issue         -> order_consumption (the only issuing path this
#                            phase builds; no standalone kitchen-issue
#                            workflow exists, and inventing one would mean
#                            an unreachable code)
#   recipe consumption    -> order_consumption
#   adjustment            -> positive_adjustment / negative_adjustment
#   waste, damage, expiry -> wastage (the *reason* is recorded on
#                            wastage_records.reason_category, which includes
#                            damage and expiry — one ledger code, precise
#                            reasons, rather than three codes whose
#                            distinction lives nowhere else)
#   return                -> supplier_return / customer_return
#   transfer              -> transfer_out / transfer_in
#   count correction      -> stock_count_adjustment
#   reservation, release  -> order_reservation / reservation_release
#   (plus)                -> opening_balance, reversal
MOVEMENT_TYPES = (
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
)

# Sign convention (documented in DATABASE_AND_API.md section 9.8):
# `quantity_delta` is signed and always expressed in the item's base unit.
#   > 0  stock enters on-hand at this location/batch
#   < 0  stock leaves on-hand at this location/batch
#   = 0  never valid for on-hand movements
# Reservation movements are the one exception: they do not change on-hand at
# all, they move quantity between "available" and "reserved" on the same
# balance row. They therefore carry a POSITIVE `quantity_delta` describing
# the magnitude reserved (order_reservation) or un-reserved
# (reservation_release), and `affects_on_hand = FALSE`.
RESERVATION_MOVEMENT_TYPES = ("order_reservation", "reservation_release")

# Types that decrease on-hand stock. Used by the posting service to assert
# the sign matches the type rather than trusting a caller-supplied sign.
OUTBOUND_MOVEMENT_TYPES = (
    "order_consumption",
    "wastage",
    "negative_adjustment",
    "transfer_out",
    "supplier_return",
)
INBOUND_MOVEMENT_TYPES = (
    "opening_balance",
    "purchase_receipt",
    "positive_adjustment",
    "transfer_in",
    "customer_return",
)


class StockMovement(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """DATABASE_AND_API.md section 9.3 — the append-only stock ledger and the
    single source of truth for all stock (this phase's own instruction:
    "Stock Ledger Is the Source of Truth... Never change stock silently").

    Nothing in `app.inventory` ever UPDATEs or DELETEs a posted row. A
    mistake is corrected by posting a compensating `reversal` movement that
    points back at the original via `source_movement_id`, and the original
    is marked reversed only through `reversed_by_movement_id` /
    `reversed_at` (metadata about the correction, not a change to the
    recorded fact). `app.inventory.ledger` is the only module permitted to
    insert here.

    Uses AppendOnlyTimestampMixin (created_at only, no updated_at) rather
    than TimestampMixin, matching the same choice OrderStatusHistory and
    LeadStatusHistory already make for history tables — an append-only row
    has no meaningful "last updated" time.
    """

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(f"movement_type IN {MOVEMENT_TYPES!r}", name="valid_movement_type"),
        CheckConstraint("quantity_delta <> 0", name="quantity_delta_non_zero"),
        # Enforces the sign convention in the database, not just in service
        # code: a reservation movement never touches on-hand and always
        # carries a positive magnitude; every on-hand movement's sign must
        # match its direction.
        CheckConstraint(
            "(movement_type IN ('order_reservation', 'reservation_release') "
            "AND NOT affects_on_hand AND quantity_delta > 0) "
            "OR (movement_type NOT IN ('order_reservation', 'reservation_release') "
            "AND affects_on_hand)",
            name="reservation_movements_do_not_affect_on_hand",
        ),
        CheckConstraint(
            "unit_cost_minor IS NULL OR unit_cost_minor >= 0", name="valid_unit_cost_minor"
        ),
        Index("ix_stock_movements_item_occurred", "inventory_item_id", "occurred_at"),
        Index("ix_stock_movements_location_occurred", "storage_location_id", "occurred_at"),
        Index("ix_stock_movements_batch_id", "batch_id"),
        Index("ix_stock_movements_type_occurred", "movement_type", "occurred_at"),
        Index("ix_stock_movements_reference", "reference_type", "reference_id"),
        Index("ix_stock_movements_performed_by", "performed_by"),
        Index("ix_stock_movements_occurred_at", "occurred_at"),
        # The balance-projection rebuild and the per-item/location balance
        # recomputation both scan by (item, location) and sum deltas.
        Index(
            "ix_stock_movements_balance_rebuild",
            "inventory_item_id",
            "storage_location_id",
            "batch_id",
        ),
        # DATABASE_AND_API.md section 9.3's documented
        # `idempotency_key VARCHAR(160) NULL UNIQUE`. Partial so the many
        # rows that legitimately have no key (manual operator actions) do not
        # collide with each other on NULL.
        Index(
            "uq_stock_movements_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    movement_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    storage_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_batches.id"), nullable=True
    )
    movement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Always in the item's base unit. The unit the operator actually entered
    # is preserved in `entered_unit_id` + `entered_quantity` so a receipt in
    # boxes remains auditable as boxes.
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    entered_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units_of_measure.id"), nullable=True
    )
    entered_quantity: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True)
    affects_on_hand: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    unit_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_value_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    # Set on `transfer_in` (pointing at its paired `transfer_out`) and on
    # `reversal` (pointing at the movement being reversed), so both halves
    # of a transfer and both sides of a correction are always traceable.
    source_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_movements.id"), nullable=True
    )
    reversed_by_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_movements.id"), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    movement_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
