"""Typed achievement domain errors — same shape as app.loyalty.errors."""

from fastapi import status


class AchievementError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "achievement_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DuplicateAchievementCodeError(AchievementError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_achievement_code"


class AchievementNotActiveError(AchievementError):
    code = "achievement_not_active"


class NotEligibleError(AchievementError):
    code = "not_eligible"


class AlreadyAwardedError(AchievementError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_awarded"


class CooldownNotElapsedError(AchievementError):
    code = "cooldown_not_elapsed"


class AlreadyReversedError(AchievementError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_reversed"
