"""Typed commercial-risk domain errors — same shape as app.loyalty.errors."""

from fastapi import status


class CommercialRiskError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "commercial_risk_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidStatusTransitionError(CommercialRiskError):
    code = "invalid_status_transition"
