"""Typed dead-letter domain errors — same shape as app.reports.errors."""

from fastapi import status


class DeadLetterError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "dead_letter_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DeadLetterNotFoundError(DeadLetterError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "dead_letter_not_found"


class ReplayNotEligibleError(DeadLetterError):
    status_code = status.HTTP_409_CONFLICT
    code = "replay_not_eligible"
