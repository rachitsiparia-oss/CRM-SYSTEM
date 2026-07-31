"""Deterministic benefit calculation — GROWTH_AND_INTELLIGENCE.md section
6.6/6.11: "evaluation is deterministic", "server is authoritative".

`benefit_rule` is a per-`offer_type` Pydantic model (validated at offer
creation, never accepted as arbitrary JSON at redemption time) turned into
an integer minor-unit discount by `compute_discount`. This module never
touches the database or order line items directly — the caller (the
order/checkout integration, task #201) is responsible for resolving
`eligible_amount_minor`: the pre-discount amount the offer's scope
(whole order / matching items / matching category / delivery fee / the
free item's price) applies against. Keeping that resolution outside this
module is what lets the same benefit math run identically in preview,
checkout, and historical redemption review, per section 6.6's "same order
must be used in preview, checkout, persisted order totals, invoices,
refunds, and reports."

`loyalty_bonus`, `internal_credit`, and `service_recovery` are non-monetary
or credit-granting benefits — `compute_discount` returns 0 for the order
discount and the caller reads `grant_amount_minor`/`grant_points` off the
validated rule to drive the loyalty/credit ledger integration separately.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

BenefitOfferType = Literal[
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
]


class PercentageBenefit(BaseModel):
    kind: Literal["percentage"] = "percentage"
    percent: Decimal = Field(gt=0, le=100)


class FixedAmountBenefit(BaseModel):
    kind: Literal["fixed_amount"] = "fixed_amount"
    amount_minor: int = Field(gt=0)


class BuyXGetYBenefit(BaseModel):
    kind: Literal["buy_x_get_y"] = "buy_x_get_y"
    buy_quantity: int = Field(gt=0)
    get_quantity: int = Field(gt=0)
    get_discount_percent: Decimal = Field(gt=0, le=100)


class ComboPriceBenefit(BaseModel):
    kind: Literal["combo_price"] = "combo_price"
    fixed_price_minor: int = Field(ge=0)


class LoyaltyBonusBenefit(BaseModel):
    kind: Literal["loyalty_bonus"] = "loyalty_bonus"
    grant_points: int = Field(gt=0)


class InternalCreditBenefit(BaseModel):
    kind: Literal["internal_credit"] = "internal_credit"
    grant_amount_minor: int = Field(gt=0)


BenefitRule = Annotated[
    PercentageBenefit
    | FixedAmountBenefit
    | BuyXGetYBenefit
    | ComboPriceBenefit
    | LoyaltyBonusBenefit
    | InternalCreditBenefit,
    Field(discriminator="kind"),
]

# Which BenefitRule "kind"(s) a given offer_type accepts.
_ALLOWED_BENEFIT_KINDS: dict[str, tuple[str, ...]] = {
    "percentage_discount": ("percentage",),
    "fixed_discount": ("fixed_amount",),
    "item_discount": ("percentage", "fixed_amount"),
    "category_discount": ("percentage", "fixed_amount"),
    "buy_x_get_y": ("buy_x_get_y",),
    "combo_price": ("combo_price",),
    "free_item": ("fixed_amount",),
    "delivery_fee_discount": ("percentage", "fixed_amount"),
    "loyalty_bonus": ("loyalty_bonus",),
    "internal_credit": ("internal_credit",),
    "service_recovery": ("percentage", "fixed_amount"),
}


def validate_benefit_kind_for_offer_type(offer_type: str, benefit: BenefitRule) -> None:
    allowed = _ALLOWED_BENEFIT_KINDS.get(offer_type, ())
    if benefit.kind not in allowed:
        raise ValueError(
            f"offer_type={offer_type!r} does not accept a {benefit.kind!r} benefit rule "
            f"(allowed: {allowed!r})."
        )


def _round_minor(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute_discount(
    *,
    benefit: BenefitRule,
    eligible_amount_minor: int,
    maximum_discount_minor: int | None = None,
) -> int:
    """Returns the discount in integer minor units, never more than
    `eligible_amount_minor` and never more than `maximum_discount_minor`
    when set. Non-monetary benefit kinds return 0 here — the caller reads
    `grant_points`/`grant_amount_minor` off `benefit` directly."""
    if eligible_amount_minor <= 0:
        return 0

    discount: int
    if isinstance(benefit, PercentageBenefit):
        discount = _round_minor(Decimal(eligible_amount_minor) * benefit.percent / Decimal(100))
    elif isinstance(benefit, FixedAmountBenefit):
        discount = benefit.amount_minor
    elif isinstance(benefit, BuyXGetYBenefit):
        # Caller passes eligible_amount_minor = the price of the "get"
        # item(s) actually qualifying, already multiplied by quantity.
        discount = _round_minor(
            Decimal(eligible_amount_minor) * benefit.get_discount_percent / Decimal(100)
        )
    elif isinstance(benefit, ComboPriceBenefit):
        discount = max(0, eligible_amount_minor - benefit.fixed_price_minor)
    else:
        # LoyaltyBonusBenefit / InternalCreditBenefit — not an order
        # discount at all.
        return 0

    discount = min(discount, eligible_amount_minor)
    if maximum_discount_minor is not None:
        discount = min(discount, maximum_discount_minor)
    return max(0, discount)
