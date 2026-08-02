"""Typed integration domain errors — same shape as app.reports.errors."""

from fastapi import status


class IntegrationError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "integration_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class IntegrationNotFoundError(IntegrationError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "integration_not_found"
