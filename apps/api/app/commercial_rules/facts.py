"""Resolves every fact in `SUPPORTED_FACTS` from real CRM data. This is the
only place a fact name is turned into an actual query — the evaluator never
touches the database directly.

Customer-level facts favor the cached roll-up columns Phase 5 already
maintains on `customers` (`completed_order_count`, `lifetime_value_minor`,
`average_order_value_minor`, `last_order_at`) over live aggregation, the
same "read from the maintained projection, don't re-derive it" choice
`StockBalance`/`LoyaltyAccount` make for their own domains. Facts with no
such projection (rolling spend, visit/no-show/cancellation counts,
referral count) are computed live with bounded, indexed queries.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Customer,
    CustomerConsent,
    CustomerTag,
    GiftCard,
    LoyaltyAccount,
    LoyaltyTier,
    Order,
    ReferralRelationship,
    Reservation,
    Segment,
    SegmentMembership,
    Tag,
)

_ROLLING_WINDOW_DAYS = 90


async def resolve_customer_facts(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    program_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Every `customer.*` fact for one customer. `program_id` scopes the
    loyalty facts to a specific program's account; when omitted, the
    default active program's account is used if the customer has one.
    """
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise ValueError(f"Customer {customer_id} not found.")

    now = datetime.now(UTC)
    facts: dict[str, Any] = {
        "customer.created_at": customer.created_at,
        "customer.days_since_created": (now - customer.created_at).days,
        "customer.lifetime_spend_minor": customer.lifetime_value_minor,
        "customer.completed_order_count": customer.completed_order_count,
        "customer.average_order_value_minor": customer.average_order_value_minor,
        "customer.days_since_last_order": (
            (now - customer.last_order_at).days if customer.last_order_at else None
        ),
        "customer.birthday_month": (
            customer.date_of_birth.month if customer.date_of_birth else None
        ),
    }

    rolling_since = now - timedelta(days=_ROLLING_WINDOW_DAYS)
    rolling_spend = await session.scalar(
        select(func.coalesce(func.sum(Order.grand_total_minor), 0)).where(
            Order.customer_id == customer_id,
            Order.status == "completed",
            Order.created_at >= rolling_since,
        )
    )
    facts["customer.rolling_90d_spend_minor"] = int(rolling_spend or 0)

    visit_count = await session.scalar(
        select(func.count()).where(
            Reservation.customer_id == customer_id, Reservation.status == "completed"
        )
    )
    facts["customer.visit_count"] = int(visit_count or 0)

    no_show_count = await session.scalar(
        select(func.count()).where(
            Reservation.customer_id == customer_id, Reservation.status == "no_show"
        )
    )
    facts["customer.no_show_count"] = int(no_show_count or 0)

    cancellation_count = await session.scalar(
        select(func.count()).where(
            Reservation.customer_id == customer_id,
            Reservation.status.in_(["cancelled_by_customer", "cancelled_by_restaurant"]),
        )
    )
    facts["customer.cancellation_count"] = int(cancellation_count or 0)

    loyalty_query = select(LoyaltyAccount).where(LoyaltyAccount.customer_id == customer_id)
    if program_id is not None:
        loyalty_query = loyalty_query.where(LoyaltyAccount.program_id == program_id)
    account = await session.scalar(loyalty_query)
    if account is not None:
        facts["customer.loyalty_points_balance"] = account.points_balance
        tier_rank = None
        if account.current_tier_id is not None:
            tier = await session.get(LoyaltyTier, account.current_tier_id)
            tier_rank = tier.rank if tier is not None else None
        facts["customer.loyalty_tier_rank"] = tier_rank
    else:
        facts["customer.loyalty_points_balance"] = 0
        facts["customer.loyalty_tier_rank"] = None

    tag_rows = await session.execute(
        select(Tag.name)
        .join(CustomerTag, CustomerTag.tag_id == Tag.id)
        .where(CustomerTag.customer_id == customer_id)
    )
    facts["customer.tags"] = [row[0] for row in tag_rows]

    # Current static membership per segment is the most recent row for
    # (segment_id, customer_id) — matches SegmentMembership's own
    # documented "add/remove history, computed at read time" contract.
    latest_membership = (
        select(
            SegmentMembership.segment_id,
            func.max(SegmentMembership.created_at).label("latest_at"),
        )
        .where(SegmentMembership.customer_id == customer_id)
        .group_by(SegmentMembership.segment_id)
        .subquery()
    )
    segment_rows = await session.execute(
        select(Segment.code)
        .join(SegmentMembership, SegmentMembership.segment_id == Segment.id)
        .join(
            latest_membership,
            (SegmentMembership.segment_id == latest_membership.c.segment_id)
            & (SegmentMembership.created_at == latest_membership.c.latest_at),
        )
        .where(SegmentMembership.customer_id == customer_id, SegmentMembership.action == "added")
    )
    facts["customer.segment_codes"] = [row[0] for row in segment_rows]

    consent_rows = await session.execute(
        select(CustomerConsent.consent_type).where(
            CustomerConsent.customer_id == customer_id, CustomerConsent.status == "granted"
        )
    )
    granted = {row[0] for row in consent_rows}
    facts["customer.whatsapp_consent"] = "whatsapp_marketing" in granted
    facts["customer.email_consent"] = "email_marketing" in granted
    facts["customer.sms_consent"] = "sms_marketing" in granted

    referral_count = await session.scalar(
        select(func.count()).where(
            ReferralRelationship.referrer_customer_id == customer_id,
            ReferralRelationship.status == "rewarded",
        )
    )
    facts["customer.referral_count"] = int(referral_count or 0)

    has_gift_card = await session.scalar(
        select(func.count()).where(GiftCard.purchaser_customer_id == customer_id)
    )
    facts["customer.has_purchased_gift_card"] = bool(has_gift_card)

    return facts


def order_context_facts(
    *,
    channel: str | None,
    order_type: str | None,
    subtotal_minor: int,
    product_ids: list[str],
    category_ids: list[str],
) -> dict[str, Any]:
    """`order.*` facts, supplied by the caller evaluating an offer at
    checkout — never resolved from the database here, since the order may
    still be a draft/preview at evaluation time."""
    return {
        "order.channel": channel,
        "order.order_type": order_type,
        "order.subtotal_minor": subtotal_minor,
        "order.product_ids": product_ids,
        "order.category_ids": category_ids,
    }
