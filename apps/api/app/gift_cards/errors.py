"""Typed gift card domain errors — same shape as app.loyalty.errors."""

from fastapi import status


class GiftCardError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "gift_card_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidStatusTransitionError(GiftCardError):
    code = "invalid_status_transition"


class GiftCardNotRedeemableError(GiftCardError):
    code = "gift_card_not_redeemable"


class InsufficientBalanceError(GiftCardError):
    code = "insufficient_balance"


class InvalidCodeError(GiftCardError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "invalid_code"


class InvalidPinError(GiftCardError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "invalid_pin"


class AlreadyReversedError(GiftCardError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_reversed"


class DuplicateIdempotencyKeyError(GiftCardError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_idempotency_key"
