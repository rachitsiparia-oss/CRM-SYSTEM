"""Typed campaign domain errors — same shape as app.loyalty.errors."""

from fastapi import status


class CampaignError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "campaign_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DuplicateCampaignCodeError(CampaignError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_campaign_code"


class InvalidStatusTransitionError(CampaignError):
    code = "invalid_status_transition"


class AudienceNotBuiltError(CampaignError):
    code = "audience_not_built"
