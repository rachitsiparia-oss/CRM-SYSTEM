import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 8.2 ("food_type VARCHAR(32) NOT NULL" without
# enumerating values). A product's fundamental classification stays binary;
# is_jain_capable/is_vegan_capable (already documented) describe whether it
# CAN be prepared that way, not a third base type — this keeps the doc's own
# is_*_capable pair meaningful instead of redundant with food_type.
FOOD_TYPES = ("vegetarian", "non_vegetarian")

# CORE_CRM_MODULES.md section 7.8 ("Sources") — the full documented closed
# set. Only 'manual' and 'override' are reachable through Phase 6 service
# code: 'inventory_derived' requires Phase 8 (Inventory) to exist,
# 'schedule' requires a scheduling feature not in this phase's scope, and
# 'integration' requires an approved external menu sync this project has
# none of yet. Kept in the CHECK constraint now so those phases don't need
# a migration just to widen it.
AVAILABILITY_SOURCES = ("manual", "inventory_derived", "schedule", "integration", "override")

# Not enumerated by any canonical document; a small controlled set added
# during Phase 6 implementation, matching the pattern
# Customer.spice_preference already established in Phase 5.
SPICE_LEVELS = ("mild", "medium", "hot", "extra_hot")


class Product(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 8.2, CORE_CRM_MODULES.md sections 7.4-7.5,
    7.8, 7.12.

    Fields beyond the documented column list, all required by this phase's
    own explicit feature list and CORE_CRM_MODULES.md section 7.12's
    allergen fields, are called out individually below rather than in one
    blanket note, since each has its own reasoning.
    """

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(f"food_type IN {FOOD_TYPES!r}", name="valid_food_type"),
        CheckConstraint(
            f"availability_source IN {AVAILABILITY_SOURCES!r}", name="valid_availability_source"
        ),
        CheckConstraint(
            f"spice_level IS NULL OR spice_level IN {SPICE_LEVELS!r}", name="valid_spice_level"
        ),
        CheckConstraint("base_price_minor >= 0", name="valid_base_price_minor"),
        CheckConstraint(
            "preparation_minutes IS NULL OR preparation_minutes >= 0",
            name="valid_preparation_minutes",
        ),
        CheckConstraint("calories IS NULL OR calories >= 0", name="valid_calories"),
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        Index("ix_products_category_id", "category_id"),
        Index(
            "ix_products_active",
            "category_id",
            "sort_order",
            postgresql_where=text("deleted_at IS NULL AND is_active"),
        ),
        Index("ix_products_name", "name"),
    )

    # DATABASE_AND_API.md's product_code — this phase's own request for a
    # "SKU/internal code" is the same field, not a second one; SKU and
    # internal product code mean the same thing for a single-location
    # restaurant with no separate warehouse SKU scheme.
    product_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # A free-text placeholder for a future barcode/scanner integration —
    # this phase's own request ("barcode placeholder"), not validated
    # against any real barcode format or scanner yet.
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("menu_categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    # Customer/menu-facing name when it should differ from the internal
    # `name` (e.g. seasonal or promotional copy) — this phase's own
    # request; falls back to `name` when unset, same pattern as
    # Customer.display_name in Phase 5.
    display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(240), nullable=True)
    food_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_jain_capable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_vegan_capable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # CORE_CRM_MODULES.md section 7.12's documented allergen/composition
    # fields, plus 'alcohol' from this phase's own request — modeled as a
    # closed set of booleans (not a free-form tag list) so it stays a
    # queryable, indexed-filterable set rather than an unbounded JSON blob
    # (CLAUDE.md section 5.3 forbids the latter for core searchable data).
    contains_egg: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_dairy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_gluten: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_nuts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_soy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_alcohol: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    spice_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    preparation_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    availability_source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    manual_override_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    manual_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # This phase's own request for per-channel availability — no real
    # ordering channel exists until Phase 7 (Orders), so these are simple
    # booleans staff configure in advance rather than something Orders
    # reads from yet.
    dine_in_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    takeaway_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    delivery_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Mirrors whichever ProductImage row has is_thumbnail=True — kept in
    # sync by app.menu.service so the documented column stays authoritative
    # for "the one image" call sites while product_images (this phase's
    # "image gallery" request, undocumented as its own table) holds the
    # full ordered set.
    image_storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_chef_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
