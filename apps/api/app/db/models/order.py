import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# This phase's own explicit source list (8 values). CORE_CRM_MODULES.md
# section 6.2 and PROJECT_PLAN.md section 10.1 document a larger 9-value
# set (pos, walk_in, website, whatsapp, phone, zomato, swiggy, third_party,
# manual) that also assumes real POS/Zomato/Swiggy integrations this
# project has none of yet (CLAUDE.md section 16, "Do not claim... any
# service integration is available without verified API or export
# capability"). This phase's instruction gives the authoritative 8-value
# list for the CRM-side foundation being built now; a real integration
# adapter can widen this list with its own migration when it exists.
ORDER_SOURCES = (
    "pos",
    "walk_in",
    "website",
    "whatsapp",
    "phone_call",
    "zomato",
    "swiggy",
    "manual",
)

ORDER_TYPES = ("dine_in", "takeaway", "delivery")

# This phase's own explicit strict state machine (7 values). The documented
# 16-value lifecycle (DATABASE_AND_API.md section 10.1, CORE_CRM_MODULES.md
# section 6.3) includes payment-gateway states (pending_payment,
# payment_verification_pending), a multi-step refund workflow, and
# delivery-partner states — all of which need capabilities this phase's own
# "DO NOT BUILD" list explicitly forbids (payment gateway integration,
# delivery-partner tracking). Implementing the fuller list would mean
# either building those forbidden capabilities or adding unreachable status
# values, neither of which is correct. This phase's explicit instruction is
# authoritative for this exact deliverable (CLAUDE.md section 1.1: a
# document "does not override... unless the user explicitly approves the
# change" — this instruction is that explicit approval). Refunds are
# tracked via `payment_status = 'refunded'` (see order_payments), not a
# separate order-status branch. See app.orders.states for the transition
# table.
ORDER_STATUSES = (
    "draft",
    "pending_confirmation",
    "confirmed",
    "preparing",
    "ready",
    "completed",
    "cancelled",
)

# This phase's own explicit payment-status list.
PAYMENT_STATUSES = ("pending", "partial", "paid", "refunded", "failed")


class Order(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """This phase's own ORDER MODEL field list. `SoftDeleteMixin.deleted_at`
    is the "Archive Status" field — the same soft-delete pattern every other
    archivable entity in this project uses, not a second mechanism.
    """

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(f"source IN {ORDER_SOURCES!r}", name="valid_source"),
        CheckConstraint(f"order_type IN {ORDER_TYPES!r}", name="valid_order_type"),
        CheckConstraint(f"status IN {ORDER_STATUSES!r}", name="valid_status"),
        CheckConstraint(f"payment_status IN {PAYMENT_STATUSES!r}", name="valid_payment_status"),
        CheckConstraint("subtotal_minor >= 0", name="valid_subtotal_minor"),
        CheckConstraint("discount_minor >= 0", name="valid_discount_minor"),
        CheckConstraint("tax_minor >= 0", name="valid_tax_minor"),
        CheckConstraint("charges_minor >= 0", name="valid_charges_minor"),
        CheckConstraint("grand_total_minor >= 0", name="valid_grand_total_minor"),
        Index("ix_orders_status_created_at", "status", "created_at"),
        Index("ix_orders_source_created_at", "source", "created_at"),
        Index("ix_orders_payment_status", "payment_status"),
        Index("ix_orders_assigned_staff_id", "assigned_staff_id"),
        Index("ix_orders_customer_id", "customer_id"),
        Index(
            "ix_orders_active",
            "status",
            "created_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_orders_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    payment_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    discount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    # Sum of the itemized order_charges rows (packaging, delivery, service,
    # etc.) — a Phase 7 implementation decision to normalize itemized
    # charges into their own table (this phase's own instruction: "Only
    # normalize where it actually improves the design"), the same
    # summary-column-plus-itemized-table pattern discount_minor/
    # order_discounts and tax_minor/order_taxes already use here.
    charges_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    grand_total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_completion_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Order-creation idempotency (this phase's own instruction: "Idempotency
    # where appropriate" — mirrors Lead.conversion_idempotency_key).
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
