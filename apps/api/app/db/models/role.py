from sqlalchemy import Boolean, CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# PROJECT_PLAN.md section 4.3 and DATABASE_AND_API.md section 4.3 — the
# canonical 15 system role codes. This tuple is only used for the CHECK
# constraint below; it is not a second permission registry.
SYSTEM_ROLE_CODES = (
    "owner",
    "general_manager",
    "operations_manager",
    "finance_manager",
    "kitchen_manager",
    "inventory_manager",
    "reservation_manager",
    "customer_support_agent",
    "marketing_manager",
    "hr_manager",
    "shift_supervisor",
    "kitchen_staff",
    "front_of_house_staff",
    "delivery_coordinator",
    "read_only_auditor",
)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Staff role — DATABASE_AND_API.md section 4.3."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (CheckConstraint("code = lower(code)", name="lowercase_code"),)
