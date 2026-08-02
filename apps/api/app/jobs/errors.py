"""Typed job-execution errors — same shape as app.reports.errors."""

from fastapi import status


class JobError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "job_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LockNotAcquiredError(JobError):
    """Raised when a distributed advisory lock is already held — the
    correct, expected outcome when a second worker instance's cron tick
    overlaps with one still running, not a failure to surface to a user."""

    code = "lock_not_acquired"


class JobNotFoundError(JobError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "job_not_found"


class JobNotReplayableError(JobError):
    status_code = status.HTTP_409_CONFLICT
    code = "job_not_replayable"
