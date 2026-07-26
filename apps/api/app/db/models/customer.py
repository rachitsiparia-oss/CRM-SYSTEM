import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 6.1.
CUSTOMER_TYPES = ("individual", "corporate")

# Not enumerated in DATABASE_AND_API.md section 6.1 (only `DEFAULT 'active'`
# is specified there); the lifecycle values below are a Phase 5 decision
# following the same pattern staff_users.account_status already uses —
# 'archived' and 'merged' are ordinary status values (toggled by the
# archive/restore actions and set once by the merge workflow), not a
# separate soft-delete mechanism. SoftDeleteMixin's deleted_at stays
# available but is not driven by these actions.
CUSTOMER_STATUSES = ("active", "inactive", "blacklisted", "archived", "merged")

# DATABASE_AND_API.md section 6.1 ("Customer segments must remain
# consistent with PROJECT_PLAN.md").
CUSTOMER_SEGMENTS = (
    "new",
    "repeat",
    "loyal",
    "vip",
    "at_risk",
    "dormant",
    "high_aov",
    "family",
    "corporate",
    "college_group",
    "delivery_first",
    "dine_in_first",
    "discount_sensitive",
    "complaint_recovery",
)

# Not enumerated by any canonical document; a small controlled set added
# during Phase 5 implementation, consistent with CORE_CRM_MODULES.md
# section 4.12's dietary examples.
DIETARY_PREFERENCES = ("vegetarian", "non_vegetarian", "vegan", "jain", "no_preference")
SPICE_PREFERENCES = ("mild", "medium", "spicy", "extra_spicy")


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 6.1.

    Order-derived metrics (completed_order_count, lifetime_value_minor,
    average_order_value_minor, first/last_order_at) stay at their zero/NULL
    defaults until Phase 7 (Orders) actually writes them — CLAUDE.md
    section 5 ("Customer lifetime value and order counts update only after
    eligible completed orders") and this phase's own instruction not to
    fabricate metrics. Nothing in Phase 5 sets them to anything else.
    """

    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint(f"customer_type IN {CUSTOMER_TYPES!r}", name="valid_customer_type"),
        CheckConstraint(f"customer_status IN {CUSTOMER_STATUSES!r}", name="valid_customer_status"),
        CheckConstraint(
            f"customer_segment IS NULL OR customer_segment IN {CUSTOMER_SEGMENTS!r}",
            name="valid_customer_segment",
        ),
        CheckConstraint(
            f"dietary_preference IS NULL OR dietary_preference IN {DIETARY_PREFERENCES!r}",
            name="valid_dietary_preference",
        ),
        CheckConstraint(
            f"spice_preference IS NULL OR spice_preference IN {SPICE_PREFERENCES!r}",
            name="valid_spice_preference",
        ),
        Index("ix_customers_primary_phone_e164", "primary_phone_e164"),
        Index("ix_customers_primary_email", "primary_email"),
        Index("ix_customers_status_segment", "customer_status", "customer_segment"),
        Index("ix_customers_assigned_staff_id", "assigned_staff_id"),
        Index("ix_customers_last_order_at", "last_order_at"),
        Index(
            "ix_customers_active",
            "customer_status",
            postgresql_where=text("deleted_at IS NULL AND customer_status = 'active'"),
        ),
    )

    customer_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    customer_type: Mapped[str] = mapped_column(String(32), nullable=False, default="individual")
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    primary_phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    primary_email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    anniversary_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    dietary_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    spice_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    customer_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    customer_segment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    acquisition_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    first_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_value_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    average_order_value_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Fast current-state pointer, added during Phase 5 implementation as a
    # complement to customer_merge_events (the immutable audit trail of
    # every merge). Section 6.7's table stores history; this column answers
    # "is this record merged, and into what" without a join.
    merged_into_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
