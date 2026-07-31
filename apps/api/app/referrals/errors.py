"""Typed referral domain errors — same shape as app.loyalty.errors."""

from fastapi import status


class ReferralError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "referral_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DuplicateProgramCodeError(ReferralError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_program_code"


class InvalidStatusTransitionError(ReferralError):
    code = "invalid_status_transition"


class ProgramNotActiveError(ReferralError):
    code = "program_not_active"


class MaxActiveCodesReachedError(ReferralError):
    status_code = status.HTTP_409_CONFLICT
    code = "max_active_codes_reached"


class SelfReferralError(ReferralError):
    code = "self_referral"


class DuplicateRefereeError(ReferralError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_referee"


class DuplicateQualifyingOrderError(ReferralError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_qualifying_order"


class InvalidRelationshipStateError(ReferralError):
    status_code = status.HTTP_409_CONFLICT
    code = "invalid_relationship_state"


class RewardHoldNotElapsedError(ReferralError):
    code = "reward_hold_not_elapsed"
