import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CustomerPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DATABASE_AND_API.md section 6.3.

    `favorite_product_note` replaces the documented
    `favorite_product_id UUID REFERENCES products(id)` for Phase 5: the
    `products` table does not exist until Phase 6, so this is a free-text
    interim field per this phase's own instruction not to link to
    not-yet-existing menu entities. Phase 6 should add the real
    `favorite_product_id` column alongside (not instead of) this one, since
    staff may have already recorded a free-text favorite that doesn't match
    any catalogue item exactly.
    """

    __tablename__ = "customer_preferences"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), unique=True, nullable=False
    )
    vegetarian: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vegan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    jain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allergen_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    favorite_product_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preferred_order_channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_seating_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
