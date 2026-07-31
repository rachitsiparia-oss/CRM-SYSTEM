"""Offer eligibility evaluation and the reserve -> confirm/reject/reverse
redemption lifecycle — GROWTH_AND_INTELLIGENCE.md section 6.6/6.7/6.8/6.11.

Evaluation combines deterministic, offer-field-level checks (status,
validity window, channel, product/category scope, minimum order value,
usage limits, coupon usability) with the constrained `eligibility_rule`
evaluated through the shared `app.commercial_rules` engine — never
arbitrary code. `Offer.redemption_count`/`Coupon.redemption_count` are
read and incremented under `SELECT ... FOR UPDATE` the same way
`app.loyalty.ledger` locks the account balance, so two concurrent
reservations against the last unit of a capped offer serialize rather
than both succeeding (section 6.10's "two concurrent uses of last
available redemption", section 6.11's "limits are concurrency-safe").

Cross-offer stackability/exclusivity (whether two offers may apply to the
same order together) requires visibility of every redemption already
applied to that order and is therefore the order/checkout integration's
responsibility (task #201), not this module's — this module only
evaluates one offer against one candidate order context at a time.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time

from app.audit.service import record_audit_event
from app.commercial_rules.evaluator import evaluate as evaluate_rule
from app.commercial_rules.facts import order_context_facts, resolve_customer_facts
from app.commercial_rules.schema import RuleEvaluationResult, RuleNode
from app.db.models import Coupon, Offer, OfferRedemption, OfferVersion, StaffUser
from app.offers import coupons as coupons_service
from app.offers.benefit import BenefitRule, compute_discount
from app.offers.errors import (
    CouponNotFoundError,
    CouponNotUsableError,
    DuplicateIdempotencyKeyError,
    InvalidRedemptionStateError,
    NotEligibleError,
    OfferNotRedeemableError,
    RedemptionLimitReachedError,
)
from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_rule_node_adapter: TypeAdapter[RuleNode] = TypeAdapter(RuleNode)
_benefit_rule_adapter: TypeAdapter[BenefitRule] = TypeAdapter(BenefitRule)


class EvaluationOutcome:
    def __init__(
        self,
        *,
        rule_result: RuleEvaluationResult,
        reasons: list[str],
        discount_amount_minor: int,
        coupon: Coupon | None,
    ) -> None:
        self.rule_result = rule_result
        self.reasons = reasons
        self.discount_amount_minor = discount_amount_minor
        self.coupon = coupon

    @property
    def eligible(self) -> bool:
        return self.rule_result.eligible and not self.reasons


def _within_day_time_window(window: dict[str, object] | None, *, now: datetime) -> bool:
    if not window:
        return True
    days = window.get("days")
    if isinstance(days, list) and days and now.weekday() not in days:
        return False
    start_raw = window.get("start_time")
    end_raw = window.get("end_time")
    if isinstance(start_raw, str) and isinstance(end_raw, str):
        start = time.fromisoformat(start_raw)
        end = time.fromisoformat(end_raw)
        current = now.time()
        if start <= end:
            if not (start <= current <= end):
                return False
        elif not (current >= start or current <= end):
            return False
    return True


async def evaluate_offer(
    session: AsyncSession,
    *,
    offer: Offer,
    version: OfferVersion,
    customer_id: uuid.UUID,
    coupon_code: str | None,
    order_channel: str | None,
    order_type: str | None,
    subtotal_minor: int,
    product_ids: list[str],
    category_ids: list[str],
    eligible_amount_minor: int,
) -> EvaluationOutcome:
    reasons: list[str] = []
    now = datetime.now(UTC)

    if offer.status != "active":
        reasons.append("offer_not_active")
    if now < version.valid_from or (version.valid_until is not None and now > version.valid_until):
        reasons.append("outside_valid_window")
    if not _within_day_time_window(version.day_time_windows, now=now):
        reasons.append("outside_day_time_window")
    if version.channel_eligibility and order_channel not in version.channel_eligibility:
        reasons.append("channel_not_eligible")
    if version.applicable_product_ids and not (
        set(version.applicable_product_ids) & set(product_ids)
    ):
        reasons.append("no_matching_products")
    if version.applicable_category_ids and not (
        set(version.applicable_category_ids) & set(category_ids)
    ):
        reasons.append("no_matching_categories")
    if version.excluded_product_ids and (set(version.excluded_product_ids) & set(product_ids)):
        reasons.append("excluded_product_present")
    if (
        version.minimum_order_value_minor is not None
        and subtotal_minor < version.minimum_order_value_minor
    ):
        reasons.append("below_minimum_order_value")
    if (
        version.global_usage_limit is not None
        and offer.redemption_count >= version.global_usage_limit
    ):
        reasons.append("global_usage_limit_reached")

    if version.per_customer_usage_limit is not None:
        customer_uses = await session.scalar(
            select(func.count())
            .select_from(OfferRedemption)
            .where(
                OfferRedemption.offer_id == offer.id,
                OfferRedemption.customer_id == customer_id,
                OfferRedemption.status.in_(["reserved", "applied", "confirmed"]),
            )
        )
        if (customer_uses or 0) >= version.per_customer_usage_limit:
            reasons.append("per_customer_usage_limit_reached")

    coupon: Coupon | None = None
    if offer.requires_code:
        if not coupon_code:
            reasons.append("coupon_code_required")
        else:
            coupon = await coupons_service.get_coupon_by_code(session, coupon_code)
            if coupon is None or coupon.offer_id != offer.id:
                reasons.append("coupon_not_found")
            else:
                usability_issue = coupons_service.is_coupon_usable(
                    coupon, customer_id=customer_id, now=now
                )
                if usability_issue is not None:
                    reasons.append(usability_issue)

    facts = await resolve_customer_facts(session, customer_id=customer_id)
    facts.update(
        order_context_facts(
            channel=order_channel,
            order_type=order_type,
            subtotal_minor=subtotal_minor,
            product_ids=product_ids,
            category_ids=category_ids,
        )
    )
    node = _rule_node_adapter.validate_python(version.eligibility_rule)
    rule_result = evaluate_rule(node, facts)

    benefit_obj = _benefit_rule_adapter.validate_python(version.benefit_rule)
    discount = 0
    if rule_result.eligible and not reasons:
        remaining_budget: int | None = None
        if offer.budget_cap_minor is not None:
            spent = await session.scalar(
                select(func.coalesce(func.sum(OfferRedemption.discount_amount_minor), 0)).where(
                    OfferRedemption.offer_id == offer.id,
                    OfferRedemption.status.in_(["reserved", "applied", "confirmed"]),
                )
            )
            remaining_budget = max(0, offer.budget_cap_minor - int(spent or 0))

        discount = compute_discount(
            benefit=benefit_obj,
            eligible_amount_minor=eligible_amount_minor,
            maximum_discount_minor=version.maximum_discount_minor,
        )
        if remaining_budget is not None:
            if remaining_budget <= 0:
                reasons.append("budget_cap_reached")
                discount = 0
            else:
                discount = min(discount, remaining_budget)

    return EvaluationOutcome(
        rule_result=rule_result, reasons=reasons, discount_amount_minor=discount, coupon=coupon
    )


async def _lock_offer(session: AsyncSession, offer_id: uuid.UUID) -> Offer:
    offer = await session.scalar(select(Offer).where(Offer.id == offer_id).with_for_update())
    if offer is None:
        raise ValueError(f"Offer {offer_id} not found.")
    return offer


async def find_by_idempotency_key(
    session: AsyncSession, idempotency_key: str
) -> OfferRedemption | None:
    result: OfferRedemption | None = await session.scalar(
        select(OfferRedemption).where(OfferRedemption.idempotency_key == idempotency_key)
    )
    return result


async def reserve(
    session: AsyncSession,
    *,
    offer_id: uuid.UUID,
    customer_id: uuid.UUID,
    coupon_code: str | None,
    order_id: uuid.UUID | None,
    order_channel: str | None,
    order_type: str | None,
    subtotal_minor: int,
    product_ids: list[str],
    category_ids: list[str],
    eligible_amount_minor: int,
    idempotency_key: str,
    actor: StaffUser | None,
) -> OfferRedemption:
    existing = await find_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        raise DuplicateIdempotencyKeyError(
            f"A redemption with idempotency key {idempotency_key!r} already exists."
        )

    offer = await _lock_offer(session, offer_id)
    if offer.status != "active":
        raise OfferNotRedeemableError(f"Offer {offer.offer_code!r} is not active.")
    version_id = offer.latest_version_id
    if version_id is None:
        raise OfferNotRedeemableError(f"Offer {offer.offer_code!r} has no version.")
    version = await session.get(OfferVersion, version_id)
    if version is None:
        raise OfferNotRedeemableError(f"Offer {offer.offer_code!r}'s version is missing.")

    if (
        version.global_usage_limit is not None
        and offer.redemption_count >= version.global_usage_limit
    ):
        raise RedemptionLimitReachedError(f"Offer {offer.offer_code!r}'s usage limit is reached.")

    outcome = await evaluate_offer(
        session,
        offer=offer,
        version=version,
        customer_id=customer_id,
        coupon_code=coupon_code,
        order_channel=order_channel,
        order_type=order_type,
        subtotal_minor=subtotal_minor,
        product_ids=product_ids,
        category_ids=category_ids,
        eligible_amount_minor=eligible_amount_minor,
    )
    if not outcome.eligible:
        failure_notes = (
            outcome.reasons or outcome.rule_result.failed_facts or outcome.rule_result.unknown_facts
        )
        raise NotEligibleError(
            "Offer is not eligible for this customer/order: " + ", ".join(failure_notes)
        )

    coupon = outcome.coupon
    if coupon is not None:
        locked_coupon = await session.scalar(
            select(Coupon).where(Coupon.id == coupon.id).with_for_update()
        )
        if locked_coupon is None:
            raise CouponNotFoundError("Coupon not found.")
        issue = coupons_service.is_coupon_usable(locked_coupon, customer_id=customer_id)
        if issue is not None:
            raise CouponNotUsableError(f"Coupon is not usable: {issue}.")
        locked_coupon.redemption_count += 1
        coupon = locked_coupon

    offer.redemption_count += 1

    redemption = OfferRedemption(
        id=uuid.uuid4(),
        offer_id=offer.id,
        offer_version_id=version.id,
        coupon_id=coupon.id if coupon else None,
        customer_id=customer_id,
        order_id=order_id,
        entered_code=coupon_code,
        eligible_amount_minor=eligible_amount_minor,
        discount_amount_minor=outcome.discount_amount_minor,
        status="reserved",
        evaluation_explanation={
            "matched_facts": outcome.rule_result.matched_facts,
            "failed_facts": outcome.rule_result.failed_facts,
            "unknown_facts": outcome.rule_result.unknown_facts,
            "reasons": outcome.reasons,
        },
        idempotency_key=idempotency_key,
        reservation_expires_at=None,
    )
    session.add(redemption)
    await session.flush()
    if actor is not None:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="offer.redemption.reserved",
            target_type="offer_redemption",
            target_id=redemption.id,
            safe_metadata={
                "offer_id": str(offer.id),
                "discount_amount_minor": redemption.discount_amount_minor,
            },
        )
    return redemption


async def confirm(
    session: AsyncSession, *, redemption: OfferRedemption, order_id: uuid.UUID, actor: StaffUser
) -> OfferRedemption:
    if redemption.status != "reserved":
        raise InvalidRedemptionStateError(
            f"Redemption {redemption.id} is {redemption.status!r}, not 'reserved'."
        )
    redemption.status = "confirmed"
    redemption.order_id = order_id
    redemption.confirmed_at = datetime.now(UTC)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="offer.redemption.confirmed",
        target_type="offer_redemption",
        target_id=redemption.id,
        safe_metadata={"order_id": str(order_id)},
    )
    return redemption


async def reject(
    session: AsyncSession, *, redemption: OfferRedemption, reason: str, actor: StaffUser
) -> OfferRedemption:
    if redemption.status != "reserved":
        raise InvalidRedemptionStateError(
            f"Redemption {redemption.id} is {redemption.status!r}, not 'reserved'."
        )
    await _release_capacity(session, redemption)
    redemption.status = "rejected"
    redemption.reversal_reason = reason
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="offer.redemption.rejected",
        target_type="offer_redemption",
        target_id=redemption.id,
        safe_metadata={"reason": reason},
    )
    return redemption


async def reverse(
    session: AsyncSession, *, redemption: OfferRedemption, reason: str, actor: StaffUser
) -> OfferRedemption:
    if redemption.status != "confirmed":
        raise InvalidRedemptionStateError(
            f"Redemption {redemption.id} is {redemption.status!r}, not 'confirmed'."
        )
    await _release_capacity(session, redemption)
    redemption.status = "reversed"
    redemption.reversed_at = datetime.now(UTC)
    redemption.reversal_reason = reason
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="offer.redemption.reversed",
        target_type="offer_redemption",
        target_id=redemption.id,
        safe_metadata={"reason": reason},
    )
    return redemption


async def _release_capacity(session: AsyncSession, redemption: OfferRedemption) -> None:
    offer = await _lock_offer(session, redemption.offer_id)
    offer.redemption_count = max(0, offer.redemption_count - 1)
    if redemption.coupon_id is not None:
        coupon = await session.scalar(
            select(Coupon).where(Coupon.id == redemption.coupon_id).with_for_update()
        )
        if coupon is not None:
            coupon.redemption_count = max(0, coupon.redemption_count - 1)
    await session.flush()
