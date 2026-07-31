"""Pure unit tests of `app.offers.benefit` — deterministic minor-unit
discount math and the offer_type/benefit_kind compatibility guard. No
database needed: `compute_discount` and `validate_benefit_kind_for_offer_type`
are both pure functions over already-validated Pydantic models.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.offers.benefit import (
    BuyXGetYBenefit,
    ComboPriceBenefit,
    FixedAmountBenefit,
    LoyaltyBonusBenefit,
    PercentageBenefit,
    compute_discount,
    validate_benefit_kind_for_offer_type,
)

# --- percentage --------------------------------------------------------------


def test_percentage_benefit_computes_expected_discount() -> None:
    benefit = PercentageBenefit(percent=Decimal("10"))
    discount = compute_discount(benefit=benefit, eligible_amount_minor=100_00)
    assert discount == 10_00


def test_percentage_benefit_rounds_half_up() -> None:
    benefit = PercentageBenefit(percent=Decimal("33.33"))
    # 100 * 33.33% = 33.33 -> rounds to 33 (ROUND_HALF_UP on .33 stays 33).
    discount = compute_discount(benefit=benefit, eligible_amount_minor=100)
    assert discount == 33


def test_percentage_benefit_rounds_half_up_at_midpoint() -> None:
    benefit = PercentageBenefit(percent=Decimal("50"))
    # 1 * 50% = 0.5 -> rounds up to 1 under ROUND_HALF_UP.
    discount = compute_discount(benefit=benefit, eligible_amount_minor=1)
    assert discount == 1


def test_percentage_benefit_never_exceeds_eligible_amount() -> None:
    benefit = PercentageBenefit(percent=Decimal("100"))
    discount = compute_discount(benefit=benefit, eligible_amount_minor=500)
    assert discount == 500


# --- fixed_amount --------------------------------------------------------------


def test_fixed_amount_benefit_returns_configured_amount() -> None:
    benefit = FixedAmountBenefit(amount_minor=5_00)
    discount = compute_discount(benefit=benefit, eligible_amount_minor=100_00)
    assert discount == 5_00


def test_fixed_amount_benefit_is_capped_at_eligible_amount() -> None:
    benefit = FixedAmountBenefit(amount_minor=10_00)
    discount = compute_discount(benefit=benefit, eligible_amount_minor=3_00)
    assert discount == 3_00


# --- buy_x_get_y ---------------------------------------------------------------


def test_buy_x_get_y_benefit_discounts_the_get_items_amount() -> None:
    benefit = BuyXGetYBenefit(buy_quantity=1, get_quantity=1, get_discount_percent=Decimal("100"))
    # Caller passes eligible_amount_minor = price of the qualifying "get" item(s).
    discount = compute_discount(benefit=benefit, eligible_amount_minor=250)
    assert discount == 250


def test_buy_x_get_y_benefit_partial_percent() -> None:
    benefit = BuyXGetYBenefit(buy_quantity=2, get_quantity=1, get_discount_percent=Decimal("50"))
    discount = compute_discount(benefit=benefit, eligible_amount_minor=200)
    assert discount == 100


# --- combo_price ---------------------------------------------------------------


def test_combo_price_benefit_discounts_difference_to_fixed_price() -> None:
    benefit = ComboPriceBenefit(fixed_price_minor=300)
    discount = compute_discount(benefit=benefit, eligible_amount_minor=500)
    assert discount == 200


def test_combo_price_benefit_never_goes_negative_when_price_exceeds_eligible_amount() -> None:
    benefit = ComboPriceBenefit(fixed_price_minor=800)
    discount = compute_discount(benefit=benefit, eligible_amount_minor=500)
    assert discount == 0


# --- maximum_discount_minor cap -----------------------------------------------


def test_maximum_discount_minor_caps_a_percentage_discount() -> None:
    benefit = PercentageBenefit(percent=Decimal("50"))
    discount = compute_discount(
        benefit=benefit, eligible_amount_minor=1000, maximum_discount_minor=200
    )
    assert discount == 200


def test_maximum_discount_minor_does_not_raise_a_smaller_discount() -> None:
    benefit = PercentageBenefit(percent=Decimal("10"))
    discount = compute_discount(
        benefit=benefit, eligible_amount_minor=1000, maximum_discount_minor=500
    )
    assert discount == 100


# --- non-monetary benefit kinds return 0 ---------------------------------------


def test_loyalty_bonus_benefit_returns_zero_order_discount() -> None:
    benefit = LoyaltyBonusBenefit(grant_points=500)
    discount = compute_discount(benefit=benefit, eligible_amount_minor=1000)
    assert discount == 0


# --- eligible_amount_minor edge cases -------------------------------------------


def test_zero_eligible_amount_yields_zero_discount() -> None:
    benefit = PercentageBenefit(percent=Decimal("10"))
    discount = compute_discount(benefit=benefit, eligible_amount_minor=0)
    assert discount == 0


def test_negative_eligible_amount_yields_zero_discount() -> None:
    benefit = FixedAmountBenefit(amount_minor=500)
    discount = compute_discount(benefit=benefit, eligible_amount_minor=-100)
    assert discount == 0


# --- validate_benefit_kind_for_offer_type ---------------------------------------


def test_validate_benefit_kind_accepts_matching_pair() -> None:
    validate_benefit_kind_for_offer_type(
        "percentage_discount", PercentageBenefit(percent=Decimal("5"))
    )


def test_validate_benefit_kind_rejects_mismatched_pair() -> None:
    with pytest.raises(ValueError, match="does not accept"):
        validate_benefit_kind_for_offer_type(
            "percentage_discount", LoyaltyBonusBenefit(grant_points=10)
        )


def test_validate_benefit_kind_rejects_loyalty_bonus_kind_on_fixed_discount_offer_type() -> None:
    with pytest.raises(ValueError):
        validate_benefit_kind_for_offer_type("fixed_discount", LoyaltyBonusBenefit(grant_points=10))


def test_validate_benefit_kind_accepts_item_discount_with_either_percentage_or_fixed() -> None:
    validate_benefit_kind_for_offer_type("item_discount", PercentageBenefit(percent=Decimal("5")))
    validate_benefit_kind_for_offer_type("item_discount", FixedAmountBenefit(amount_minor=100))
