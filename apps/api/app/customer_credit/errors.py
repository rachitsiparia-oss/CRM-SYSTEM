"""Typed customer-credit domain errors — same shape as app.loyalty.errors."""

from fastapi import status


class CustomerCreditError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "customer_credit_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InsufficientCreditError(CustomerCreditError):
    code = "insufficient_credit"


class AlreadyReversedError(CustomerCreditError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_reversed"


class DuplicateIdempotencyKeyError(CustomerCreditError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_idempotency_key"


class AccountNotActiveError(CustomerCreditError):
    code = "account_not_active"
