from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# INTEGRATIONS_AUTOMATIONS_REALTIME.md section 3 — categories actually
# instantiated by this codebase today, not the full aspirational list (no
# payment/website-ordering/supplier row is seeded since none of those
# integrations exist yet; adding a category here does not imply the
# integration is built).
INTEGRATION_CATEGORIES = (
    "authentication_identity",
    "database_storage",
    "email",
    "whatsapp",
    "sms",
    "file_storage_exports",
    "ai_provider",
    "analytics_observability",
)
# Section 4.2, verbatim.
INTEGRATION_STATUSES = (
    "draft",
    "configuring",
    "validating",
    "active",
    "degraded",
    "paused",
    "disabled",
    "failed",
    "revoked",
    "archived",
)
INTEGRATION_ENVIRONMENTS = ("local", "test", "staging", "production")
# Section 23.1, verbatim.
INTEGRATION_HEALTH_STATES = ("unknown", "healthy", "degraded", "unhealthy", "disabled")


class Integration(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Cross-domain integration registry and health record —
    INTEGRATIONS_AUTOMATIONS_REALTIME.md sections 4/5/23.

    This is deliberately a read-mostly summary/health record, not a second
    place that owns provider configuration: WhatsApp/email/SMS remain
    configured on `CommunicationChannel` (Phase 10) and AI provider
    selection remains environment-variable-driven (Phase 14,
    `app.controlled_ai.providers.get_ai_provider`). A row here exists per
    known integration point so Settings has one place to see status/health
    across all of them; `credential_reference` never stores an actual
    secret value (CLAUDE.md section 24.4/6.5), only a label such as
    "OPENAI_API_KEY configured" or "not configured".
    """

    __tablename__ = "integrations"
    __table_args__ = (
        CheckConstraint(f"category IN {INTEGRATION_CATEGORIES!r}", name="valid_category"),
        CheckConstraint(f"status IN {INTEGRATION_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"environment IN {INTEGRATION_ENVIRONMENTS!r}", name="valid_environment"),
        CheckConstraint(
            f"health_state IN {INTEGRATION_HEALTH_STATES!r}", name="valid_health_state"
        ),
        UniqueConstraint("code", name="uq_integrations_code"),
        Index("ix_integrations_category", "category"),
        Index("ix_integrations_health_state", "health_state"),
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    environment: Mapped[str] = mapped_column(String(16), nullable=False, default="local")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    config_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    credential_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    credential_last_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    webhook_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    base_endpoint: Mapped[str | None] = mapped_column(String(300), nullable=True)
    default_sender: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rate_limit_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    retry_policy_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    capability_flags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    health_state: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
