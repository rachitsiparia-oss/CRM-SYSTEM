import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin


class ReservationTableAssignment(UUIDPrimaryKeyMixin, Base):
    """Which table(s) are assigned to a reservation, and for how long —
    DATABASE_AND_API.md section 11.2. A reservation may hold more than one
    table at once (merged tables for a large party), so this is a genuine
    many-to-many join, not a single fast pointer on `Reservation` the way
    `assigned_staff_id` is: `unassigned_at IS NULL` rows are "currently
    assigned," and the table itself is both the live assignment and its own
    history (the same append-oriented shape `OrderAssignment` already
    established for staff assignment).
    """

    __tablename__ = "reservation_table_assignments"
    __table_args__ = (
        Index("ix_reservation_table_assignments_reservation_id", "reservation_id"),
        Index("ix_reservation_table_assignments_table_id", "restaurant_table_id"),
        # At most one *active* assignment per (reservation, table) pair —
        # re-assigning the same table after it was unassigned is a new row,
        # not an update to the old one.
        Index(
            "uq_reservation_table_assignments_active",
            "reservation_id",
            "restaurant_table_id",
            unique=True,
            postgresql_where=text("unassigned_at IS NULL"),
        ),
    )

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id"), nullable=False
    )
    restaurant_table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("restaurant_tables.id"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
