from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReservationTag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """This phase's own instruction: "Birthday, Anniversary, VIP, Corporate,
    Repeat Guest, Large Party, Family, custom tags." Mirrors `Tag`'s shape
    exactly, but kept as its own reservation-scoped table rather than reusing
    Phase 5's customer-scoped `tags` — a reservation tag (e.g. "Large Party")
    describes the booking, not the guest, and the two vocabularies are not
    interchangeable.
    """

    __tablename__ = "reservation_tags"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
