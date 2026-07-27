import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# The inventory-side lifecycle of one order. Deliberately separate from the
# Phase 7 order status machine: an order's *stock* state is not the same
# thing as its fulfilment state, and conflating them would mean weakening
# app.orders.states (which this phase's instruction forbids).
#
#   pending    order confirmed but stock not yet processed (transient)
#   reserved   ingredients reserved, nothing deducted yet
#   consumed   reservations converted to actual deductions
#   released   reservations returned without deduction (cancelled early)
#   skipped    order has no stock-tracked ingredients to process
ORDER_INVENTORY_STATES = ("pending", "reserved", "consumed", "released", "skipped")


class OrderInventoryState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per order, tracking whether its stock has been reserved,
    consumed, or released — and holding the resolved-consumption snapshot.

    This is the **idempotency guard** for the order-to-inventory
    integration. This phase's own instruction requires that "repeated order
    events must not double-reserve or double-consume stock"; a UNIQUE
    `order_id` plus an explicit state check means a second `confirmed` or
    `preparing` transition (retry, double-click, replayed job) is a no-op
    rather than a second deduction. `stock_movements.idempotency_key` gives
    the same protection one level down, per movement.

    `consumption_snapshot` stores the fully resolved ingredient plan that was
    actually applied — which recipe (and recipe version) was chosen for each
    order line, the base-unit quantity computed, and the specific batches
    allocated. This phase's instruction requires exactly this: "Recipe
    resolution must use the recipe version effective at the time of stock
    processing or store the resolved consumption snapshot." Keeping the
    snapshot means a later recipe edit can never change the historical record
    of what an order consumed, mirroring how Phase 7's `order_items` snapshot
    product names and prices.
    """

    __tablename__ = "order_inventory_states"
    __table_args__ = (
        CheckConstraint(f"state IN {ORDER_INVENTORY_STATES!r}", name="valid_state"),
        CheckConstraint(
            "estimated_cost_minor IS NULL OR estimated_cost_minor >= 0",
            name="valid_estimated_cost_minor",
        ),
        CheckConstraint(
            "consumed_cost_minor IS NULL OR consumed_cost_minor >= 0",
            name="valid_consumed_cost_minor",
        ),
        # One inventory state per order — the structural half of the
        # idempotency guarantee.
        Index("uq_order_inventory_states_order_id", "order_id", unique=True),
        Index("ix_order_inventory_states_state", "state"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The resolved ingredient plan; see class docstring. Shape is documented
    # in app.inventory.order_integration, not enforced here — it is an
    # audit/replay artifact, never queried relationally, which is why JSONB
    # is appropriate despite CLAUDE.md section 5.3's general caution about
    # JSON blobs for *searchable relational* business data.
    consumption_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Theoretical ingredient cost at reservation time, and the cost actually
    # attributed at consumption. Both BIGINT integer minor units, per
    # CLAUDE.md section 7's non-negotiable money rule.
    estimated_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    consumed_cost_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Set when an order is cancelled *after* consumption: stock is never
    # silently restored (this phase's explicit rule), so this records that an
    # operational decision is outstanding.
    post_consumption_note: Mapped[str | None] = mapped_column(Text, nullable=True)
