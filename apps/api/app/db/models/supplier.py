from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 9.6 specifies `status VARCHAR(32) NOT NULL
# DEFAULT 'active'` without enumerating values; 'archived' follows the same
# status-plus-SoftDeleteMixin pattern Customer already established in
# Phase 5 (the archive action sets both).
SUPPLIER_STATUSES = ("active", "inactive", "archived")


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 9.6, CORE_CRM_MODULES.md section 8.13.

    Operational supplier records only. This phase's own instruction is
    explicit that supplier *finance* is out of scope ("Do not build:
    supplier invoices, accounts payable, bank reconciliation, accounting
    journal entries, procurement approval finance workflows"), so there are
    no invoice, payable, or ledger-account fields here — `payment_terms` is
    free text describing the commercial agreement, not a posting rule.

    `tax_identifier` covers CORE_CRM_MODULES.md section 8.13's address/tax
    block and this phase's "GST/tax identifier placeholder if documented"
    — stored as an opaque string with no GST validation or filing behavior
    (CLAUDE.md section 24 forbids GST filing in this project).
    """

    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint(f"status IN {SUPPLIER_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "normal_lead_time_days IS NULL OR normal_lead_time_days >= 0",
            name="valid_normal_lead_time_days",
        ),
        CheckConstraint(
            "minimum_order_value_minor IS NULL OR minimum_order_value_minor >= 0",
            name="valid_minimum_order_value_minor",
        ),
        Index("ix_suppliers_name", "name"),
        Index(
            "ix_suppliers_active",
            "name",
            postgresql_where=text("deleted_at IS NULL AND status = 'active'"),
        ),
    )

    supplier_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(160), nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)

    # DATABASE_AND_API.md section 9.6 says "address fields" without
    # enumerating them; these mirror CustomerAddress's shape (Phase 5) so
    # address handling stays consistent across the project, minus the
    # delivery-specific columns a supplier has no use for.
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="IN")

    # DATABASE_AND_API.md section 9.6's documented `supply_categories
    # TEXT[]`. Kept as the documented free-text array rather than a join
    # table to inventory_categories: the seed values in PROJECT_PLAN.md
    # section 9 are descriptive prose ("Burger buns, brownies, garlic
    # bread", "Boxes, bags, napkins, cups, cutlery") that does not map
    # one-to-one onto the inventory category list. The authoritative
    # item/supplier relationship is inventory_items.preferred_supplier_id.
    supply_categories: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    normal_lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(120), nullable=True)
    minimum_order_value_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tax_identifier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
