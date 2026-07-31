import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 7.3.
REFERRAL_RELATIONSHIP_STATUSES = (
    "invited",
    "attributed",
    "qualified",
    "rewarded",
    "rejected",
    "cancelled",
)


class ReferralRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """GROWTH_AND_INTELLIGENCE.md section 7.4's anti-abuse rules are
    enforced here at the schema level, not just in service code:

    - `referred_identity_key` is a normalized (lowercased email or E.164
      phone) key with a partial unique index, so the SAME contact identity
      can never be attributed twice — no duplicate referee attribution,
      structurally.
    - a CHECK constraint rejects `referrer_customer_id = referred_customer_id`
      once the referred contact resolves to an existing customer — no
      self-referral once both sides are known.
    - `qualifying_order_id` carries its own partial unique index so one
      order can reward at most one relationship.
    """

    __tablename__ = "referral_relationships"
    __table_args__ = (
        CheckConstraint(f"status IN {REFERRAL_RELATIONSHIP_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "referred_customer_id IS NULL OR referred_customer_id <> referrer_customer_id",
            name="no_self_referral",
        ),
        Index("ix_referral_relationships_program_id", "program_id"),
        Index("ix_referral_relationships_referrer_customer_id", "referrer_customer_id"),
        Index("ix_referral_relationships_status", "status"),
        Index(
            "uq_referral_relationships_identity",
            "program_id",
            "referred_identity_key",
            unique=True,
        ),
        Index(
            "uq_referral_relationships_qualifying_order",
            "qualifying_order_id",
            unique=True,
            postgresql_where=text("qualifying_order_id IS NOT NULL"),
        ),
    )

    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("referral_programs.id"), nullable=False
    )
    code_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("referral_codes.id"), nullable=False)
    referrer_customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    # Normalized phone or email of the referred contact — the anti-abuse
    # anchor, present even before a customer record exists for them.
    referred_identity_key: Mapped[str] = mapped_column(String(200), nullable=False)
    referred_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    attributed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    qualifying_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="invited")
    referrer_reward_ledger_entry_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    referee_reward_ledger_entry_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
