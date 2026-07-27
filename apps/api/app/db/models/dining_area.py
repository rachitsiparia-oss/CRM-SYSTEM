from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DiningArea(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """A physical seating zone within the single RKPR restaurant — never a
    branch or outlet (CLAUDE.md section 24 forbids multi-tenancy; this
    phase's own instruction repeats it for storage locations' sibling
    concept and the same reasoning applies here).

    Mirrors `StorageLocation` (Phase 8) and `InventoryCategory`/
    `MenuCategory`'s shape deliberately — the same managed-reference-table
    pattern this project already uses whenever a phase's own instruction
    needs named, orderable, archivable zones.
    """

    __tablename__ = "dining_areas"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        Index(
            "ix_dining_areas_active",
            "sort_order",
            postgresql_where=text("deleted_at IS NULL AND is_active"),
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
