import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# This phase's own instruction lists "Merged" and "Split" alongside genuine
# mutually-exclusive operational states. A table cannot simultaneously BE
# "available" and "split" — splitting is the *action* that returns two
# previously-merged tables back to their prior status, not a state either
# table persists in afterward, so it is recorded as a `table_status_history`
# event/reason rather than a seventh status value. "Temporary" describes a
# table's *nature* (an overflow table brought in for a large event), not a
# mutually-exclusive operational state — a temporary table can independently
# be available, occupied, or blocked — so it is `is_temporary`, a flag, not
# a status.
TABLE_STATUSES = (
    "available",
    "reserved",
    "occupied",
    "cleaning",
    "blocked",
    "maintenance",
    "merged",
)

TABLE_SHAPES = ("round", "square", "rectangle", "oval", "booth", "bar", "custom")


class RestaurantTable(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """A physical table within one `DiningArea` of the single RKPR
    restaurant. `status` is the fast "what is this table doing right now"
    pointer; `TableStatusHistory` preserves the full change history — the
    same fast-pointer-plus-history-table split `Order.assigned_staff_id` /
    `OrderAssignment` already established (Phase 7).
    """

    __tablename__ = "restaurant_tables"
    __table_args__ = (
        CheckConstraint(f"status IN {TABLE_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"shape IN {TABLE_SHAPES!r}", name="valid_shape"),
        CheckConstraint("capacity > 0", name="valid_capacity"),
        CheckConstraint("minimum_capacity >= 0", name="valid_minimum_capacity"),
        CheckConstraint(
            "maximum_capacity IS NULL OR maximum_capacity >= capacity",
            name="valid_maximum_capacity",
        ),
        CheckConstraint(
            "minimum_capacity <= capacity", name="minimum_capacity_not_above_capacity"
        ),
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        Index("ix_restaurant_tables_dining_area_id", "dining_area_id"),
        Index("ix_restaurant_tables_status", "status"),
        Index(
            "uq_restaurant_tables_number",
            "table_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_restaurant_tables_qr_identifier",
            "qr_identifier",
            unique=True,
            postgresql_where=text("qr_identifier IS NOT NULL"),
        ),
    )

    dining_area_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dining_areas.id"), nullable=False
    )
    table_number: Mapped[str] = mapped_column(String(20), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    maximum_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shape: Mapped[str] = mapped_column(String(16), nullable=False, default="square")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="available")
    is_wheelchair_accessible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_temporary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Set while this table is combined with another under one reservation —
    # both tables in a merge point at each other's merge group via a shared
    # value (this table's own id, held by whichever table is the merge
    # "primary"). NULL when not merged.
    merged_with_table_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("restaurant_tables.id"), nullable=True
    )
    qr_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
