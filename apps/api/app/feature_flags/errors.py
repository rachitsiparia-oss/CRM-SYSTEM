"""Typed feature-flag domain errors — same shape as app.reports.errors."""

from fastapi import status


class FeatureFlagError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "feature_flag_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class FeatureFlagNotFoundError(FeatureFlagError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "feature_flag_not_found"


class DuplicateFeatureFlagCodeError(FeatureFlagError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_feature_flag_code"
