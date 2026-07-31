import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 6.2, plus `internal_credit` — added
# under the 2026-07-30 scope-expansion decision (offers may grant internal
# credit, not only points/discounts).
OFFER_TYPES = (
    "percentage_discount",
    "fixed_discount",
    "item_discount",
    "category_discount",
    "buy_x_get_y",
    "combo_price",
    "free_item",
    "delivery_fee_discount",
    "loyalty_bonus",
    "internal_credit",
    "service_recovery",
)

# GROWTH_AND_INTELLIGENCE.md section 6.3.
OFFER_STATUSES = (
    "draft",
    "in_review",
    "approved",
    "active",
    "paused",
    "expired",
    "cancelled",
    "archived",
)


class Offer(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """The mutable "current state" pointer — `latest_version_id` always
    references the immutable snapshot in `offer_versions` that the current
    `status`/dates reflect. Mirrors the `KnowledgeArticle`/
    `KnowledgeArticleVersion` split (Phase 11): editing an offer's rule
    creates a new version row rather than mutating history, so a
    redemption's `offer_version_id` reference always resolves to exactly
    what was evaluated at the time (GROWTH_AND_INTELLIGENCE.md section
    6.8: "Later changes to the offer cannot rewrite historical order
    calculations.").

    Campaign linkage is one-directional (`Campaign.linked_offer_id`) —
    no `campaign_id` column here. A campaign referencing this offer is
    found with a reverse query rather than a second FK, which would
    otherwise create a circular table dependency with `campaigns` for no
    additional query capability.
    """

    __tablename__ = "offers"
    __table_args__ = (
        CheckConstraint(f"offer_type IN {OFFER_TYPES!r}", name="valid_offer_type"),
        CheckConstraint(f"status IN {OFFER_STATUSES!r}", name="valid_status"),
        CheckConstraint("latest_version_number >= 1", name="valid_latest_version_number"),
        Index("ix_offers_status", "status"),
        Index("ix_offers_offer_type", "offer_type"),
    )

    offer_code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    internal_name: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_facing_name: Mapped[str] = mapped_column(String(160), nullable=False)
    offer_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    requires_code: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stackability_group: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_exclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    budget_cap_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    redemption_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redemption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    financial_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    terms_and_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    latest_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("offer_versions.id"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OfferVersion(UUIDPrimaryKeyMixin, Base):
    """One immutable snapshot per material change to an offer's rule —
    GROWTH_AND_INTELLIGENCE.md section 6.8's "rule version" that every
    `OfferRedemption` pins itself to.
    """

    __tablename__ = "offer_versions"
    __table_args__ = (
        CheckConstraint("version_number >= 1", name="valid_version_number"),
        Index("uq_offer_versions_offer_number", "offer_id", "version_number", unique=True),
        Index("ix_offer_versions_offer_id", "offer_id"),
    )

    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Constrained condition tree (app.commercial_rules) — customer/order
    # eligibility. Validated at creation time, never arbitrary SQL/code.
    eligibility_rule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Benefit calculation parameters (percent/fixed amount/free item id/
    # buy-x-get-y config/points multiplier) — shape depends on offer_type,
    # validated by app.offers.schemas against a per-type Pydantic model
    # before this JSONB payload is ever persisted.
    benefit_rule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    minimum_order_value_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    maximum_discount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    applicable_product_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    excluded_product_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    applicable_category_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    channel_eligibility: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    day_time_windows: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    global_usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    per_customer_usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Coupon(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """GROWTH_AND_INTELLIGENCE.md section 6.5. `code` is normalized
    (uppercased, whitespace-stripped) before the unique index below ever
    sees it — `app.offers.coupons.normalize_code` is the single
    normalization point, matching Phase 5's phone/email normalization
    pattern.
    """

    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint(
            "redemption_limit IS NULL OR redemption_limit > 0", name="valid_redemption_limit"
        ),
        CheckConstraint("redemption_count >= 0", name="valid_redemption_count"),
        Index("uq_coupons_code", "code", unique=True),
        Index("ix_coupons_offer_id", "offer_id"),
        Index("ix_coupons_customer_id", "customer_id"),
    )

    code: Mapped[str] = mapped_column(String(40), nullable=False)
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"), nullable=False)
    is_reusable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Non-null when this coupon is issued to one specific customer (e.g. a
    # referral or campaign-personalized code); NULL for a public code.
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redemption_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redemption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id"), nullable=True
    )
    generation_batch: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


OFFER_REDEMPTION_STATUSES = ("reserved", "applied", "confirmed", "reversed", "rejected", "expired")


class OfferRedemption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """GROWTH_AND_INTELLIGENCE.md section 6.8: every applied discount stores
    its offer/coupon reference, rule version, pre-discount amount, computed
    discount, evaluation result, and application order — an immutable
    financial record even though the row itself progresses through the
    reserve -> applied -> confirmed lifecycle (status changes only, the
    calculation fields never do, per section 6.8's "cannot rewrite
    historical order calculations").
    """

    __tablename__ = "offer_redemptions"
    __table_args__ = (
        CheckConstraint(f"status IN {OFFER_REDEMPTION_STATUSES!r}", name="valid_status"),
        CheckConstraint("eligible_amount_minor >= 0", name="valid_eligible_amount_minor"),
        CheckConstraint("discount_amount_minor >= 0", name="valid_discount_amount_minor"),
        Index("ix_offer_redemptions_offer_id", "offer_id"),
        Index("ix_offer_redemptions_customer_id", "customer_id"),
        Index("ix_offer_redemptions_order_id", "order_id"),
        Index("ix_offer_redemptions_status", "status"),
        Index(
            "uq_offer_redemptions_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
    )

    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id"), nullable=False)
    offer_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_versions.id"), nullable=False
    )
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("coupons.id"), nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    entered_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    eligible_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="reserved")
    # Structured explanation — GROWTH_AND_INTELLIGENCE.md's "evaluation
    # results must be explainable": matched/failed conditions, caps
    # applied, exclusivity decisions, reason codes.
    evaluation_explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    reservation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
