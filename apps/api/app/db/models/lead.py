import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 7.1 ("Allowed statuses"). This is the
# canonical, closed list — DATABASE_AND_API.md is the authoritative
# document for schema questions per CLAUDE.md section 1.1. A later Phase 5
# instruction proposed a different 9-value list (new/contacted/interested/
# follow_up_scheduled/not_responding/converted/lost/do_not_contact/archived)
# that conflicts with this one; per that same instruction's own conflict
# rule ("follow the highest-authority project document"), this documented
# 10-value list wins. The differences are absorbed without losing anything
# real: "not_responding" is a derived signal from `last_contact_at` and the
# "leads with no contact" filter, not a stored status; "do_not_contact" is
# the separate `do_not_contact` boolean below (DATABASE_AND_API.md doesn't
# model it as a status, and it needs to coexist with any status, not
# replace one); "archived" reuses SoftDeleteMixin (the same pattern
# staff_users and customers use), not a new status value; "converted" is
# the action name (`POST /leads/{id}/convert`) that sets status to the
# documented `won` value, matching the `won_customer_id` column name.
LEAD_STATUSES = (
    "new",
    "contacted",
    "qualified",
    "interested",
    "follow_up_scheduled",
    "proposal_shared",
    "negotiating",
    "won",
    "lost",
    "closed",
)

# DATABASE_AND_API.md section 7.1 ("Allowed sources"). Covers the five
# sources named directly in a later Phase 5 instruction (Zomato ->
# zomato_import, Swiggy -> swiggy_import, Website -> website, Marketing
# Campaign -> meta_campaign/google_campaign, Offline -> walk_in) plus the
# rest of the documented set.
LEAD_SOURCES = (
    "website",
    "phone",
    "walk_in",
    "whatsapp",
    "zomato_import",
    "swiggy_import",
    "meta_campaign",
    "google_campaign",
    "referral",
    "corporate_outreach",
    "event_enquiry",
    "offline_qr",
)

# DATABASE_AND_API.md section 7.1 has `lead_type VARCHAR(32) NOT NULL`
# without enumerating values; CORE_CRM_MODULES.md section 5.2 is the
# domain-specific document for core-module product behavior and supplies
# the closed list.
LEAD_TYPES = (
    "corporate_catering",
    "recurring_office_order",
    "event_booking",
    "group_dining",
    "partnership",
    "franchise_or_business_enquiry",
    "general_sales_enquiry",
)

# Not enumerated by DATABASE_AND_API.md ("priority VARCHAR(16) NOT NULL
# DEFAULT 'normal'"); the minimal controlled set a later Phase 5
# instruction proposed.
LEAD_PRIORITIES = ("low", "normal", "high", "urgent")

# CORE_CRM_MODULES.md section 5.12 ("Example reasons") — formalized into a
# closed set for the CHECK constraint, the same treatment Phase 3 gave
# other documents' "representative examples" lists.
LOST_REASONS = (
    "budget",
    "timing",
    "no_response",
    "chose_competitor",
    "service_unavailable",
    "location_issue",
    "menu_mismatch",
    "duplicate",
    "invalid_enquiry",
)


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 7.1."""

    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(f"lead_type IN {LEAD_TYPES!r}", name="valid_lead_type"),
        CheckConstraint(f"source IN {LEAD_SOURCES!r}", name="valid_source"),
        CheckConstraint(f"status IN {LEAD_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"priority IN {LEAD_PRIORITIES!r}", name="valid_priority"),
        CheckConstraint(
            f"lost_reason IS NULL OR lost_reason IN {LOST_REASONS!r}", name="valid_lost_reason"
        ),
        Index("ix_leads_status_created_at", "status", "created_at"),
        Index("ix_leads_source_created_at", "source", "created_at"),
        Index("ix_leads_assigned_staff_next_follow_up", "assigned_staff_id", "next_follow_up_at"),
        Index("ix_leads_requested_date", "requested_date"),
        Index("ix_leads_priority", "priority"),
        Index(
            "ix_leads_active",
            "status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_leads_conversion_idempotency_key",
            "conversion_idempotency_key",
            unique=True,
            postgresql_where=text("conversion_idempotency_key IS NOT NULL"),
        ),
    )

    lead_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    lead_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    organization_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    # Interim free-text replacement for the documented
    # `campaign_id UUID REFERENCES campaigns(id)` — the campaigns table
    # does not exist until Phase 12, per this phase's own instruction not
    # to link to not-yet-existing entities.
    campaign_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    estimated_value_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    party_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requested_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    requested_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    next_follow_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    won_customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    lost_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extensions added during Phase 5 implementation, beyond the documented
    # column list:
    do_not_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qualification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    food_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    conversion_idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
