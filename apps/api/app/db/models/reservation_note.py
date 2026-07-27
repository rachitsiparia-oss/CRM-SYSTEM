import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin

# This phase's own instruction's note categories: "Internal notes, Kitchen
# notes, Guest preferences, Allergies reference, Special occasions,
# Accessibility, Celebration, VIP." `allergy` deliberately only *references*
# allergen information — it never duplicates `Customer`'s own dietary/
# allergen fields (Phase 5), matching this phase's own "no duplicated data"
# instruction.
RESERVATION_NOTE_TYPES = (
    "internal",
    "kitchen",
    "guest_preference",
    "allergy",
    "special_occasion",
    "accessibility",
    "celebration",
    "vip",
)


class ReservationNote(UUIDPrimaryKeyMixin, Base):
    """Structured, individually-timestamped note history — mirrors
    `OrderNote`'s edit/soft-delete pattern exactly.
    """

    __tablename__ = "reservation_notes"
    __table_args__ = (
        CheckConstraint(f"note_type IN {RESERVATION_NOTE_TYPES!r}", name="valid_note_type"),
        Index("ix_reservation_notes_reservation_id", "reservation_id"),
    )

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id"), nullable=False
    )
    note_type: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
