"""Typed service-recovery domain errors — same shape as
app.complaints.errors."""

from fastapi import status


class ServiceRecoveryError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "service_recovery_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidActionStatusTransitionError(ServiceRecoveryError):
    code = "invalid_action_status_transition"


class ApprovalNotRequiredError(ServiceRecoveryError):
    code = "approval_not_required"


class SelfApprovalNotAllowedError(ServiceRecoveryError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "self_approval_not_allowed"


class NotApprovedError(ServiceRecoveryError):
    code = "not_approved"


class AlreadyExecutedError(ServiceRecoveryError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_executed"


class UnsupportedRecoveryTypeError(ServiceRecoveryError):
    code = "unsupported_recovery_type"
