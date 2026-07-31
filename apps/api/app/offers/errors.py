"""Typed offer/coupon/redemption domain errors — same shape as
app.loyalty.errors."""

from fastapi import status


class OfferError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "offer_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DuplicateOfferCodeError(OfferError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_offer_code"


class InvalidStatusTransitionError(OfferError):
    code = "invalid_status_transition"


class InvalidBenefitRuleError(OfferError):
    code = "invalid_benefit_rule"


class DuplicateCouponCodeError(OfferError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_coupon_code"


class CouponNotFoundError(OfferError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "coupon_not_found"


class CouponNotUsableError(OfferError):
    code = "coupon_not_usable"


class OfferNotRedeemableError(OfferError):
    code = "offer_not_redeemable"


class NotEligibleError(OfferError):
    code = "not_eligible"


class RedemptionLimitReachedError(OfferError):
    status_code = status.HTTP_409_CONFLICT
    code = "redemption_limit_reached"


class DuplicateIdempotencyKeyError(OfferError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_idempotency_key"


class InvalidRedemptionStateError(OfferError):
    status_code = status.HTTP_409_CONFLICT
    code = "invalid_redemption_state"
