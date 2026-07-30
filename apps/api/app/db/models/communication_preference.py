import uuid
from datetime import time

from sqlalchemy import Boolean, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


# One row per customer, current-state only — the append-only change log
# lives in `CommunicationConsent`. Transactional and promotional are
# separate booleans per channel (this phase's own instruction: "marketing
# opt-out should not automatically block essential transactional ...
# messages unless explicitly required"), so an opted-out-of-marketing
# customer still receives their order-ready WhatsApp message.
class CommunicationPreference(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    __tablename__ = "communication_preferences"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), unique=True, nullable=False
    )
    preferred_channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=True
    )
    allow_transactional_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_transactional_sms: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_transactional_whatsapp: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    allow_promotional_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_promotional_sms: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_promotional_whatsapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiet_hours_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    language_preference: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
