from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


class FeatureFlag(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A simple on/off switch for gating a backend or frontend capability at
    runtime — CLAUDE.md section 21's "Allow optional integrations to remain
    disabled without crashing unrelated modules" generalized to any
    feature, not a generic rule/targeting engine. No percentage rollout, no
    per-role targeting: those are exactly the kind of no-code
    customization surface CLAUDE.md section 2 forbids. `code` is the
    stable lookup key application code checks against."""

    __tablename__ = "feature_flags"
    __table_args__ = (UniqueConstraint("code", name="uq_feature_flags_code"),)

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
