"""add phase6 menu and product management

Revision ID: b36e4b05396d
Revises: 523aed98ebd1
Create Date: 2026-07-26 13:49:48.474633

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b36e4b05396d"
down_revision: str | Sequence[str] | None = "523aed98ebd1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MENU_TABLES = (
    "menu_categories",
    "modifier_groups",
    "modifiers",
    "modifier_group_items",
    "products",
    "product_images",
    "product_modifier_groups",
    "product_variants",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "menu_categories",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_menu_categories_valid_sort_order")),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["staff_users.id"],
            name=op.f("fk_menu_categories_created_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"],
            ["staff_users.id"],
            name=op.f("fk_menu_categories_deleted_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["staff_users.id"],
            name=op.f("fk_menu_categories_updated_by_staff_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_menu_categories")),
        sa.UniqueConstraint("code", name=op.f("uq_menu_categories_code")),
    )
    op.create_index(
        "ix_menu_categories_active",
        "menu_categories",
        ["sort_order"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND is_active"),
    )

    op.create_table(
        "modifier_groups",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("min_select", sa.Integer(), nullable=False),
        sa.Column("max_select", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("max_select >= 1", name=op.f("ck_modifier_groups_valid_max_select")),
        sa.CheckConstraint(
            "max_select >= min_select",
            name=op.f("ck_modifier_groups_max_select_at_least_min_select"),
        ),
        sa.CheckConstraint("min_select >= 0", name=op.f("ck_modifier_groups_valid_min_select")),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_modifier_groups_valid_sort_order")),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["staff_users.id"],
            name=op.f("fk_modifier_groups_created_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"],
            ["staff_users.id"],
            name=op.f("fk_modifier_groups_deleted_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["staff_users.id"],
            name=op.f("fk_modifier_groups_updated_by_staff_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_modifier_groups")),
    )

    op.create_table(
        "modifiers",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("default_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "default_price_minor >= 0", name=op.f("ck_modifiers_valid_default_price")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["staff_users.id"], name=op.f("fk_modifiers_created_by_staff_users")
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"], ["staff_users.id"], name=op.f("fk_modifiers_deleted_by_staff_users")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["staff_users.id"], name=op.f("fk_modifiers_updated_by_staff_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_modifiers")),
    )

    op.create_table(
        "modifier_group_items",
        sa.Column("modifier_group_id", sa.Uuid(), nullable=False),
        sa.Column("modifier_id", sa.Uuid(), nullable=False),
        sa.Column("price_minor_override", sa.BigInteger(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "price_minor_override IS NULL OR price_minor_override >= 0",
            name=op.f("ck_modifier_group_items_valid_price_minor_override"),
        ),
        sa.CheckConstraint(
            "sort_order >= 0", name=op.f("ck_modifier_group_items_valid_sort_order")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["staff_users.id"],
            name=op.f("fk_modifier_group_items_created_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["modifier_group_id"],
            ["modifier_groups.id"],
            name=op.f("fk_modifier_group_items_modifier_group_id_modifier_groups"),
        ),
        sa.ForeignKeyConstraint(
            ["modifier_id"],
            ["modifiers.id"],
            name=op.f("fk_modifier_group_items_modifier_id_modifiers"),
        ),
        sa.PrimaryKeyConstraint("modifier_group_id", "modifier_id", name="pk_modifier_group_items"),
    )

    op.create_table(
        "products",
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("display_name", sa.String(length=180), nullable=True),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.String(length=240), nullable=True),
        sa.Column("food_type", sa.String(length=32), nullable=False),
        sa.Column("is_jain_capable", sa.Boolean(), nullable=False),
        sa.Column("is_vegan_capable", sa.Boolean(), nullable=False),
        sa.Column("contains_egg", sa.Boolean(), nullable=False),
        sa.Column("contains_dairy", sa.Boolean(), nullable=False),
        sa.Column("contains_gluten", sa.Boolean(), nullable=False),
        sa.Column("contains_nuts", sa.Boolean(), nullable=False),
        sa.Column("contains_soy", sa.Boolean(), nullable=False),
        sa.Column("contains_alcohol", sa.Boolean(), nullable=False),
        sa.Column("spice_level", sa.String(length=16), nullable=True),
        sa.Column("preparation_minutes", sa.Integer(), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("base_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("tax_category", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("availability_source", sa.String(length=32), nullable=False),
        sa.Column("manual_override_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manual_override_reason", sa.Text(), nullable=True),
        sa.Column("dine_in_available", sa.Boolean(), nullable=False),
        sa.Column("takeaway_available", sa.Boolean(), nullable=False),
        sa.Column("delivery_available", sa.Boolean(), nullable=False),
        sa.Column("image_storage_path", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("is_chef_recommended", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "availability_source IN "
            "('manual', 'inventory_derived', 'schedule', 'integration', 'override')",
            name=op.f("ck_products_valid_availability_source"),
        ),
        sa.CheckConstraint(
            "food_type IN ('vegetarian', 'non_vegetarian')",
            name=op.f("ck_products_valid_food_type"),
        ),
        sa.CheckConstraint(
            "spice_level IS NULL OR spice_level IN ('mild', 'medium', 'hot', 'extra_hot')",
            name=op.f("ck_products_valid_spice_level"),
        ),
        sa.CheckConstraint(
            "base_price_minor >= 0", name=op.f("ck_products_valid_base_price_minor")
        ),
        sa.CheckConstraint(
            "calories IS NULL OR calories >= 0", name=op.f("ck_products_valid_calories")
        ),
        sa.CheckConstraint(
            "preparation_minutes IS NULL OR preparation_minutes >= 0",
            name=op.f("ck_products_valid_preparation_minutes"),
        ),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_products_valid_sort_order")),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["menu_categories.id"],
            name=op.f("fk_products_category_id_menu_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["staff_users.id"], name=op.f("fk_products_created_by_staff_users")
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"], ["staff_users.id"], name=op.f("fk_products_deleted_by_staff_users")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["staff_users.id"], name=op.f("fk_products_updated_by_staff_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("barcode", name=op.f("uq_products_barcode")),
        sa.UniqueConstraint("product_code", name=op.f("uq_products_product_code")),
        sa.UniqueConstraint("slug", name=op.f("uq_products_slug")),
    )
    op.create_index(
        "ix_products_active",
        "products",
        ["category_id", "sort_order"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND is_active"),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)
    op.create_index("ix_products_name", "products", ["name"], unique=False)

    op.create_table(
        "product_images",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("alt_text", sa.String(length=200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_thumbnail", sa.Boolean(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "file_size_bytes > 0", name=op.f("ck_product_images_valid_file_size_bytes")
        ),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_product_images_valid_sort_order")),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["staff_users.id"],
            name=op.f("fk_product_images_created_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_product_images_product_id_products")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_images")),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"], unique=False)
    op.create_index(
        "uq_product_images_thumbnail_per_product",
        "product_images",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_thumbnail"),
    )

    op.create_table(
        "product_modifier_groups",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("modifier_group_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sort_order >= 0", name=op.f("ck_product_modifier_groups_valid_sort_order")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["staff_users.id"],
            name=op.f("fk_product_modifier_groups_created_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["modifier_group_id"],
            ["modifier_groups.id"],
            name=op.f("fk_product_modifier_groups_modifier_group_id_modifier_groups"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_product_modifier_groups_product_id_products"),
        ),
        sa.PrimaryKeyConstraint(
            "product_id", "modifier_group_id", name="pk_product_modifier_groups"
        ),
    )

    op.create_table(
        "product_variants",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("preparation_minutes", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.Column("deletion_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "preparation_minutes IS NULL OR preparation_minutes >= 0",
            name=op.f("ck_product_variants_valid_preparation_minutes"),
        ),
        sa.CheckConstraint("price_minor >= 0", name=op.f("ck_product_variants_valid_price_minor")),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_product_variants_valid_sort_order")),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["staff_users.id"],
            name=op.f("fk_product_variants_created_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"],
            ["staff_users.id"],
            name=op.f("fk_product_variants_deleted_by_staff_users"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_product_variants_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["staff_users.id"],
            name=op.f("fk_product_variants_updated_by_staff_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_variants")),
        sa.UniqueConstraint("code", name=op.f("uq_product_variants_code")),
    )
    op.create_index(
        "ix_product_variants_product_id", "product_variants", ["product_id"], unique=False
    )

    # Supabase's PostgREST layer is reachable via the public anon key unless
    # RLS blocks it, even though apps/api's own connection (table-owning
    # role) is unaffected — SECURITY_PERFORMANCE_AND_QUALITY.md section 8.5,
    # the same convention every table-creating migration since Phase 3 has
    # followed.
    for table_name in _MENU_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")

    op.drop_table("product_modifier_groups")

    op.drop_index(
        "uq_product_images_thumbnail_per_product",
        table_name="product_images",
        postgresql_where=sa.text("is_thumbnail"),
    )
    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_table("product_images")

    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_index(
        "ix_products_active",
        table_name="products",
        postgresql_where=sa.text("deleted_at IS NULL AND is_active"),
    )
    op.drop_table("products")

    op.drop_table("modifier_group_items")
    op.drop_table("modifiers")
    op.drop_table("modifier_groups")

    op.drop_index(
        "ix_menu_categories_active",
        table_name="menu_categories",
        postgresql_where=sa.text("deleted_at IS NULL AND is_active"),
    )
    op.drop_table("menu_categories")
