"""The single canonical normalization service for phone numbers, email
addresses, tag names, and search text — reused by both `app.customers` and
`app.leads` (and any future module that needs it) rather than
reimplemented per module, per this phase's own instruction not to
duplicate normalization logic between routers, schemas, and models.

Phone normalization is deterministic and India-only (no `phonenumbers` or
similar dependency): RKPR is a single-location Bengaluru restaurant
(PROJECT_PLAN.md section 3), and no canonical document approves a general
international phone library. If international numbers become a real
requirement, this is the one place to add it.
"""

import re

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_NON_DIGIT = re.compile(r"[^\d+]")
_WHITESPACE = re.compile(r"\s+")


class NormalizationError(ValueError):
    """Raised when input cannot be normalized into a valid value — the
    caller (a Pydantic validator) turns this into a 422 validation_error,
    never a raw 500."""


def normalize_phone(raw: str | None) -> str | None:
    """Returns E.164 (`+91XXXXXXXXXX`) or None for empty input. Raises
    NormalizationError for anything that isn't a plausible Indian number."""
    if raw is None or not raw.strip():
        return None

    cleaned = _NON_DIGIT.sub("", raw.strip())
    has_plus = cleaned.startswith("+")
    digits = cleaned.lstrip("+")

    if has_plus:
        if not (8 <= len(digits) <= 15):
            raise NormalizationError(f"Phone number is not a valid length: {raw!r}")
        return f"+{digits}"

    # Strip a leading international/trunk prefix down to the bare number.
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]

    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"

    raise NormalizationError(f"Phone number is not a valid Indian number: {raw!r}")


def normalize_email(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    candidate = raw.strip().lower()
    if not _EMAIL_PATTERN.match(candidate):
        raise NormalizationError(f"Email address is not valid: {raw!r}")
    return candidate


def normalize_tag_name(raw: str) -> str:
    collapsed = _WHITESPACE.sub(" ", raw.strip()).lower()
    if not collapsed:
        raise NormalizationError("Tag name cannot be empty.")
    return collapsed


def normalize_search_text(raw: str) -> str:
    return _WHITESPACE.sub(" ", raw.strip()).lower()
