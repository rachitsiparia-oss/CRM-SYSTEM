"""Typed operational-settings domain errors — same shape as
app.reports.errors."""

from fastapi import status


class OperationalSettingsError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "operational_settings_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class OperationalSettingsNotSeededError(OperationalSettingsError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "operational_settings_not_seeded"
