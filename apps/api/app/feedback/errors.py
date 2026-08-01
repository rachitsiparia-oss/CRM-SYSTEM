"""Typed feedback/review-request domain errors — same shape as
app.achievements.errors."""

from fastapi import status


class FeedbackError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "feedback_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidStatusTransitionError(FeedbackError):
    code = "invalid_status_transition"


class AlreadyConvertedError(FeedbackError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_converted"


class DuplicateReviewRequestError(FeedbackError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_review_request"


class ReviewRequestNotEligibleError(FeedbackError):
    code = "review_request_not_eligible"


class InvalidReviewRequestTransitionError(FeedbackError):
    code = "invalid_review_request_transition"
