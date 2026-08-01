import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    AppendOnlyTimestampMixin,
    AuditedMixin,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

# GROWTH_AND_INTELLIGENCE.md section 13.2.
REPORTING_AREAS = (
    "executive",
    "sales",
    "orders",
    "customers",
    "leads",
    "reservations",
    "menu_products",
    "inventory_suppliers",
    "marketing",
    "loyalty",
    "feedback",
    "complaints",
    "communication",
    "staff_tasks",
    "system_operations",
)
# GROWTH_AND_INTELLIGENCE.md section 13.3. `custom` requires an explicit
# bounded window on the run/request, validated in the service layer rather
# than at the DB level (the definition only records the *default*).
REPORT_WINDOWS = (
    "today",
    "yesterday",
    "current_week",
    "previous_week",
    "current_month",
    "previous_month",
    "current_quarter",
    "previous_quarter",
    "custom",
)
REPORT_DEFINITION_TYPES = ("system", "custom")
REPORT_DEFINITION_VISIBILITIES = ("private", "shared", "system")
REPORT_SHARE_PERMISSION_LEVELS = ("view", "run")


class ReportDefinition(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A saved, reusable report configuration — GROWTH_AND_INTELLIGENCE.md
    section 13 and the Phase 14 instruction's report-definition schema
    requirement. `metric_codes`/`dimensions`/`default_filters` reference the
    in-code `app.analytics_core` metric registry by code, never raw SQL or
    table/column names (CLAUDE.md's "never accept arbitrary sort columns,
    raw SQL filters" rule extended to reporting).

    System-seeded definitions (`definition_type="system"`) are read-only
    templates covering the canonical reporting areas; `custom` definitions
    are user-built via the report builder and owned by their creator.
    """

    __tablename__ = "report_definitions"
    __table_args__ = (
        CheckConstraint(f"domain IN {REPORTING_AREAS!r}", name="valid_domain"),
        CheckConstraint(
            f"definition_type IN {REPORT_DEFINITION_TYPES!r}", name="valid_definition_type"
        ),
        CheckConstraint(f"default_window IN {REPORT_WINDOWS!r}", name="valid_default_window"),
        CheckConstraint(
            f"visibility IN {REPORT_DEFINITION_VISIBILITIES!r}", name="valid_visibility"
        ),
        Index("uq_report_definitions_code", "code", unique=True),
        Index("ix_report_definitions_domain", "domain"),
        Index("ix_report_definitions_owner_staff_id", "owner_staff_id"),
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(String(24), nullable=False)
    definition_type: Mapped[str] = mapped_column(String(16), nullable=False, default="custom")
    metric_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    dimensions: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    default_filters: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    default_window: Mapped[str] = mapped_column(String(20), nullable=False, default="current_month")
    comparison_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    owner_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="private")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class ReportDefinitionShare(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Grants view/run access to a `visibility="shared"` definition beyond
    its owner — either to one staff member or to every holder of a role
    code (validated against `app.permissions.role_matrix` at the service
    layer, matching how other phases reference role codes without a second
    roles-table FK)."""

    __tablename__ = "report_definition_shares"
    __table_args__ = (
        CheckConstraint(
            "(shared_with_staff_id IS NOT NULL) != (shared_with_role_code IS NOT NULL)",
            name="exactly_one_share_target",
        ),
        CheckConstraint(
            f"permission_level IN {REPORT_SHARE_PERMISSION_LEVELS!r}", name="valid_permission_level"
        ),
        Index("ix_report_definition_shares_report_definition_id", "report_definition_id"),
        Index(
            "uq_report_definition_shares_staff",
            "report_definition_id",
            "shared_with_staff_id",
            unique=True,
            postgresql_where=text("shared_with_staff_id IS NOT NULL"),
        ),
        Index(
            "uq_report_definition_shares_role",
            "report_definition_id",
            "shared_with_role_code",
            unique=True,
            postgresql_where=text("shared_with_role_code IS NOT NULL"),
        ),
    )

    report_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_definitions.id"), nullable=False
    )
    shared_with_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    shared_with_role_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    permission_level: Mapped[str] = mapped_column(String(8), nullable=False, default="view")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
