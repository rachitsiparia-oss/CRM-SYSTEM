import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 6.6.
CONSENT_TYPES = (
    "whatsapp_marketing",
    "email_marketing",
    "sms_marketing",
    "loyalty",
    "feedback_request",
    "personalization",
)

# Not enumerated by the canonical document ("status VARCHAR(32) NOT NULL"
# with no allowed-values list); a minimal, obvious set added during Phase 5
# implementation.
CONSENT_STATUSES = ("granted", "withdrawn", "unknown")


class CustomerConsent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DATABASE_AND_API.md section 6.6.

    One current row per (customer_id, consent_type) — the simpler of the
    two options the document offers ("unique constraint... or append-only
    history with one current pointer"). granted_at/withdrawn_at track the
    current row's own transition times, which is enough for "marketing
    actions must use the current consent state at send time"
    (CORE_CRM_MODULES.md section 4.13) without a second history table.
    """

    __tablename__ = "customer_consents"
    __table_args__ = (
        CheckConstraint(f"consent_type IN {CONSENT_TYPES!r}", name="valid_consent_type"),
        CheckConstraint(f"status IN {CONSENT_STATUSES!r}", name="valid_status"),
        UniqueConstraint("customer_id", "consent_type", name="uq_customer_consents_customer_type"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    captured_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
