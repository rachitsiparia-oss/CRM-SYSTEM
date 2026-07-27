import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# Only conversions within the same unit type are permitted (this phase's own
# instruction: "Do not allow conversions such as kilograms to litres. Do not
# invent density-based conversion in this phase.").
UNIT_TYPES = ("weight", "volume", "count")


class UnitOfMeasure(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """A managed unit-of-measure catalogue.

    DATABASE_AND_API.md section 9.1 models a unit as a bare
    `unit_of_measure VARCHAR(32)` column on `inventory_items`. This phase's
    own instruction requires exact-decimal conversion between compatible
    units ("1 kilogram = 1000 grams", "only allow conversions within
    compatible unit types", "all conversion factors must use exact decimal
    storage") — which a bare string cannot express. Normalizing units into
    this table is therefore a functional requirement of the phase, not a
    stylistic preference; see DATABASE_AND_API.md section 9.8 for the
    recorded deviation.

    `conversion_factor` is always "how many base units is one of this unit",
    so the base unit of each type has factor 1. Conversion between two units
    of the same type is `(qty * from.factor) / to.factor`, evaluated in
    Decimal — never binary floating point (CLAUDE.md section 7's money rule
    applied to quantities, per this phase's own instruction: "Never use
    binary floating-point storage for inventory quantities, conversion
    factors or recipe quantities").
    """

    __tablename__ = "units_of_measure"
    __table_args__ = (
        CheckConstraint(f"unit_type IN {UNIT_TYPES!r}", name="valid_unit_type"),
        CheckConstraint("conversion_factor > 0", name="valid_conversion_factor"),
        CheckConstraint("decimal_places >= 0 AND decimal_places <= 3", name="valid_decimal_places"),
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        # A base unit is the one whose factor is exactly 1 and which points
        # at no other unit; every non-base unit must name its base.
        CheckConstraint(
            "(base_unit_id IS NULL AND conversion_factor = 1) OR base_unit_id IS NOT NULL",
            name="base_unit_has_unit_factor",
        ),
        Index("ix_units_of_measure_unit_type", "unit_type"),
        Index(
            "ix_units_of_measure_active",
            "unit_type",
            "sort_order",
            postgresql_where=text("deleted_at IS NULL AND is_active"),
        ),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(16), nullable=False)
    base_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("units_of_measure.id"), nullable=True
    )
    # NUMERIC(20,8) rather than the (16,3) used for quantities: a factor may
    # legitimately be a small fraction (e.g. 1 gram = 0.001 kilogram) and
    # must not lose precision when multiplied back out.
    conversion_factor: Mapped[Decimal] = mapped_column(
        Numeric(20, 8), nullable=False, default=Decimal(1)
    )
    # How many decimal places this unit is displayed/entered with. Capped at
    # 3 to match the NUMERIC(16,3) quantity storage every ledger column uses.
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
