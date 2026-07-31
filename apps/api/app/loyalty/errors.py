"""Typed loyalty domain errors — same shape as app.inventory.errors."""

from fastapi import status


class LoyaltyError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "loyalty_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InsufficientPointsError(LoyaltyError):
    code = "insufficient_points"


class AlreadyReversedError(LoyaltyError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_reversed"


class DuplicateIdempotencyKeyError(LoyaltyError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_idempotency_key"


class ProgramNotActiveError(LoyaltyError):
    code = "program_not_active"


class InvalidStatusTransitionError(LoyaltyError):
    code = "invalid_status_transition"


class DuplicateDefaultProgramError(LoyaltyError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_default_program"
