import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 12 only sketches `conversations`/`messages`/
# `message_attachments`/`communication_templates`; this phase's own
# instruction additionally requires a channel *registry* (enabled/disabled,
# provider, sender identity, inbound/outbound toggles, template requirement,
# business-hours restriction, fallback channel) distinct from a message's
# per-send channel value. No separate `communication_provider_configs`
# table is created — provider selection and its config are columns on this
# same row, the same "don't split one concept into two tables" choice
# Phase 9 made collapsing `status`/`approval_status`. No provider secret is
# ever stored here (CLAUDE.md section 16); real credentials stay in
# environment configuration, referenced only by `provider_config_key`.
CHANNEL_CODES = ("internal", "email", "sms", "whatsapp", "voice_log", "web_chat", "manual_call")


class CommunicationChannel(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A channel registry row per `CHANNEL_CODES` value — structurally the
    same managed-reference-table shape as `DiningArea`/`MenuCategory`, not
    soft-deletable (disable via `is_enabled`, matching how a dining area is
    deactivated rather than removed)."""

    __tablename__ = "communication_channels"
    __table_args__ = (
        CheckConstraint(f"code IN {CHANNEL_CODES!r}", name="valid_code"),
        CheckConstraint(
            "fallback_channel_id IS NULL OR fallback_channel_id != id",
            name="valid_fallback_channel",
        ),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_config_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    default_sender_identity: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    inbound_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    outbound_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    business_hours_restricted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fallback_channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
