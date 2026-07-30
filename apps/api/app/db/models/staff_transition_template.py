import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# Onboarding and offboarding templates are the same shape (a named plan
# header department/role targets an ordered list of steps) — consolidated
# into one `transition_type`-discriminated pair of tables rather than the
# instruction's suggested four (`onboarding_templates`/
# `onboarding_template_steps` and a parallel `offboarding_plans`/
# `offboarding_steps`), per that same instruction's "consolidate... and
# document every major decision."
TRANSITION_TYPES = ("onboarding", "offboarding")


class StaffTransitionTemplate(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    __tablename__ = "staff_transition_templates"
    __table_args__ = (
        CheckConstraint(f"transition_type IN {TRANSITION_TYPES!r}", name="valid_transition_type"),
    )

    transition_type: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
