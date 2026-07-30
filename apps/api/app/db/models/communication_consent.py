import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

CONSENT_TYPES = (
    "transactional_email",
    "promotional_email",
    "transactional_sms",
    "promotional_sms",
    "transactional_whatsapp",
    "promotional_whatsapp",
    "global",
)

CONSENT_SOURCES = (
    "customer_request",
    "staff_entry",
    "website_form",
    "implicit_transactional",
    "unsubscribe_link",
)


class CommunicationConsent(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only consent-change log (source/timestamp/version per this
    phase's own instruction section 13) — `CommunicationPreference` holds
    the derived current state; this table is why that state changed."""

    __tablename__ = "communication_consents"
    __table_args__ = (
        CheckConstraint(f"consent_type IN {CONSENT_TYPES!r}", name="valid_consent_type"),
        CheckConstraint(f"source IN {CONSENT_SOURCES!r}", name="valid_source"),
        Index("ix_communication_consents_customer_id", "customer_id"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    consent_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
