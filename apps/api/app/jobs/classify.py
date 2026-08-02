"""Retry classification and backoff — INTEGRATIONS_AUTOMATIONS_REALTIME.md
section 11. Retry only when the failure may succeed later; everything else
(a domain validation error, a permission error, a malformed input) is
permanent — retrying it would just fail again identically, so the section
11.1 "usually permanent" list is the default and only recognized transient
exception types are classified retryable.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.exc import TimeoutError as SATimeoutError

RETRY_CLASSIFICATIONS = ("retryable", "permanent")

# Deliberately narrow: connection/timeout-shaped failures only. A business
# rule violation (InvalidComplaintTransitionError and friends) is a
# subclass of Exception, not of any of these, so it correctly falls
# through to "permanent" without needing per-domain-error awareness here.
_RETRYABLE_EXCEPTION_TYPES: tuple[type[BaseException], ...] = (
    TimeoutError,
    SATimeoutError,
    ConnectionError,
    OSError,
    OperationalError,
    DBAPIError,
)


def classify_error(exc: BaseException) -> str:
    if isinstance(exc, _RETRYABLE_EXCEPTION_TYPES):
        return "retryable"
    return "permanent"


def compute_next_retry_at(
    attempt: int, *, base_seconds: int = 30, cap_seconds: int = 1800
) -> datetime:
    """Exponential backoff with jitter, capped — section 11.2. `attempt` is
    1-indexed (the attempt number that just failed)."""
    exponential = min(base_seconds * (2 ** max(attempt - 1, 0)), cap_seconds)
    jittered = exponential + random.uniform(0, exponential * 0.2)
    return datetime.now(UTC) + timedelta(seconds=jittered)
