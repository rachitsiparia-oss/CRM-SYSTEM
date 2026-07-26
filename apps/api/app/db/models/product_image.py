import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# Not its own table in DATABASE_AND_API.md section 8.2 (which only has a
# single `image_storage_path` column on `products`) — added during Phase 6
# implementation for this phase's own "image gallery" requirement and
# CORE_CRM_MODULES.md section 7.11 ("Menu images"). `products.image_storage_path`
# stays the documented column, kept in sync with whichever row here has
# is_thumbnail=True, so existing call sites that only need "the one image"
# never need to know this table exists.
#
# Deletion is a real DELETE, not soft — CLAUDE.md section 7's soft-delete
# guidance is for records needing historical retention (orders, notes,
# audit-relevant entities); a removed gallery photo is not one of those,
# and CLAUDE.md section 7 itself requires "explicit business justification"
# before treating something as needing preservation, not the reverse.
MAX_ALT_TEXT_LENGTH = 200


class ProductImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        CheckConstraint("file_size_bytes > 0", name="valid_file_size_bytes"),
        Index("ix_product_images_product_id", "product_id"),
        Index(
            "uq_product_images_thumbnail_per_product",
            "product_id",
            unique=True,
            postgresql_where=text("is_thumbnail"),
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(MAX_ALT_TEXT_LENGTH), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_thumbnail: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
