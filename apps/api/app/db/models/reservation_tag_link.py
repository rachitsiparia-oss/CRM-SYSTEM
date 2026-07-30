import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ReservationTagLink(Base):
    """Reservation-to-tag mapping — mirrors `CustomerTag`'s join shape."""

    __tablename__ = "reservation_tag_links"
    __table_args__ = (
        PrimaryKeyConstraint("reservation_id", "tag_id", name="pk_reservation_tag_links"),
    )

    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservations.id"), nullable=False)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reservation_tags.id"), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
