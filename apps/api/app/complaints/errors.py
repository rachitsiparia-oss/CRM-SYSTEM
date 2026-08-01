"""Typed complaint domain errors — same shape as app.feedback.errors."""

from fastapi import status


class ComplaintError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "complaint_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidStatusTransitionError(ComplaintError):
    code = "invalid_status_transition"


class InvalidAssignmentError(ComplaintError):
    code = "invalid_assignment"


class DuplicateEscalationError(ComplaintError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_escalation"


class SelfLinkError(ComplaintError):
    code = "self_link"
