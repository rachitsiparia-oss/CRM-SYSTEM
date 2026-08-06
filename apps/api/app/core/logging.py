import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any, cast

import structlog

from app.core.config import Settings

# Defense-in-depth beneath "only ever log explicit, named fields"
# (CLAUDE.md section 6.5 / 19): any event-dict key whose *name* matches one
# of these markers gets its value redacted regardless of call site,
# catching an accidental `logger.info(..., **kwargs)` or a mis-named field
# before it reaches stdout. This does not replace the discipline of never
# passing secrets into logger calls — it's a safety net for when that
# discipline slips, not a substitute for it.
_SENSITIVE_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "credential",
    "signing_key",
    "service_role_key",
    "signature",
    "otp",
    "card_number",
    "cvv",
    "ssn",
)


def _redact_sensitive_fields(
    logger: object, method_name: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    del logger, method_name
    for key in event_dict:
        lowered = key.lower()
        if any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS):
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Structured JSON logs with correlation IDs — CLAUDE.md section 19.

    Secrets, tokens, and payment details must never be passed into log
    events; redaction is enforced primarily by only ever logging explicit,
    named fields rather than raw request/response bodies, backed by
    `_redact_sensitive_fields` as an automated safety net.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _redact_sensitive_fields,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    return cast(structlog.typing.FilteringBoundLogger, structlog.get_logger(name))
