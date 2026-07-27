from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# Not enumerated by any canonical document; a small controlled set covering
# the storage zones CORE_CRM_MODULES.md section 8.2 and this phase's own
# instruction both name (Main Kitchen, Dry Store, Cold Storage, Freezer,
# Bar, Packaging Store).
STORAGE_LOCATION_TYPES = ("kitchen", "dry_store", "chilled", "frozen", "bar", "packaging", "other")


class StorageLocation(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """A storage location *within the single RKPR restaurant* — never a
    branch or outlet. CLAUDE.md section 24 forbids multi-tenancy and this
    phase's own instruction repeats it ("Do not implement multi-branch
    architecture. These are storage locations within the same RKPR
    Restaurant business.").

    DATABASE_AND_API.md section 9.1 models this as a bare
    `storage_zone VARCHAR(64)` column on `inventory_items`. Normalizing it
    is required by this phase's own instruction (per-location balances,
    transfers between locations, per-location stock counts, and a
    per-location negative-stock policy all need a real record to hang off).
    See DATABASE_AND_API.md section 9.8 for the recorded deviation.
    """

    __tablename__ = "storage_locations"
    __table_args__ = (
        CheckConstraint(f"location_type IN {STORAGE_LOCATION_TYPES!r}", name="valid_location_type"),
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        Index(
            "ix_storage_locations_active",
            "sort_order",
            postgresql_where=text("deleted_at IS NULL AND is_active"),
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    # Defaults to FALSE and is expected to stay FALSE: this phase's own
    # instruction permits the flag "only if explicitly approved", and
    # CORE_CRM_MODULES.md section 8.21 requires "negative stock behavior
    # follows explicit policy". Setting it true is an explicit, audited
    # per-location decision, never a silent fallback when stock runs short.
    allows_negative_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
