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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# This phase's own instruction: "draft, in_progress, submitted, approved,
# cancelled".
COUNT_STATUSES = ("draft", "in_progress", "submitted", "approved", "cancelled")

# Statuses in which a count session is still open and therefore blocks a
# second concurrent session for the same location (CORE_CRM_MODULES.md
# section 8.11's cycle-count process assumes one live count per location;
# this phase's instruction asks to "prevent duplicate active count sessions
# for the same location").
ACTIVE_COUNT_STATUSES = ("draft", "in_progress", "submitted")


class StockCount(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A physical stock-count session — CORE_CRM_MODULES.md section 8.11.

    Approval is the only step that touches stock: it posts one
    `stock_count_adjustment` movement per non-zero variance line, in a single
    transaction. The recorded `system_quantity` on each line is the snapshot
    taken when the session was started (documented step 2, "freeze or
    snapshot expected stock"), so a variance stays meaningful even if other
    movements happen while counters are walking the shelves.
    """

    __tablename__ = "stock_counts"
    __table_args__ = (
        CheckConstraint(f"status IN {COUNT_STATUSES!r}", name="valid_status"),
        Index("ix_stock_counts_location_id", "storage_location_id"),
        Index("ix_stock_counts_status_scheduled", "status", "scheduled_date"),
        # At most one open count session per location. A partial unique index
        # rather than service-only validation, so two concurrent requests
        # cannot both pass a "no active session" check and then both insert.
        Index(
            "uq_stock_counts_active_per_location",
            "storage_location_id",
            unique=True,
            postgresql_where=text("status IN ('draft', 'in_progress', 'submitted')"),
        ),
    )

    count_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    storage_location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class StockCountLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One counted item/batch within a session.

    `variance_quantity` is stored rather than computed on read because it is
    the figure the approver actually reviewed and the figure the resulting
    adjustment movement was derived from — recomputing it later against a
    since-changed system quantity would misrepresent what was approved.
    """

    __tablename__ = "stock_count_lines"
    __table_args__ = (
        CheckConstraint("system_quantity >= 0", name="valid_system_quantity"),
        CheckConstraint(
            "counted_quantity IS NULL OR counted_quantity >= 0", name="valid_counted_quantity"
        ),
        Index("ix_stock_count_lines_count_id", "count_id"),
        Index("ix_stock_count_lines_item_id", "inventory_item_id"),
    )

    count_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock_counts.id"), nullable=False)
    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id"), nullable=False
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_batches.id"), nullable=True
    )
    # Snapshot of on-hand stock when the session started.
    system_quantity: Mapped[Decimal] = mapped_column(Numeric(16, 3), nullable=False)
    # NULL until a counter records a figure — distinguishes "counted zero"
    # from "not yet counted", which matters when submitting a session.
    counted_quantity: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True)
    variance_quantity: Mapped[Decimal | None] = mapped_column(Numeric(16, 3), nullable=True)
    variance_value_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set on approval for lines that produced a correction.
    movement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_movements.id"), nullable=True
    )
