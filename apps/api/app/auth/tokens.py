"""Supabase Auth access-token verification.

Supabase issues HS256-signed JWTs using the project's JWT signing secret
(Project Settings -> API -> JWT Settings). Verifying locally with that
shared secret avoids a network round trip to Supabase on every request —
ARCHITECTURE_AND_TECH_STACK.md section 10.1 step 5 ("FastAPI validates the
token"). `AUTH_JWT_SIGNING_SECRET` must never be sent to the browser.
"""

from dataclasses import dataclass
from typing import Any

import jwt

from app.core.config import get_settings

SUPABASE_AUDIENCE = "authenticated"


class TokenValidationError(Exception):
    """Raised for any invalid, expired, malformed, or unverifiable token.

    Deliberately does not distinguish sub-reasons in its public interface —
    the caller must always respond with a generic 401, never leaking which
    specific check failed (SECURITY_PERFORMANCE_AND_QUALITY.md section 3.4,
    "generic error responses that avoid account enumeration").
    """


@dataclass(frozen=True)
class AccessTokenClaims:
    auth_user_id: str
    email: str | None
    session_id: str | None
    issued_at: int | None
    expires_at: int | None


def decode_access_token(token: str) -> AccessTokenClaims:
    settings = get_settings()
    if not settings.auth_jwt_signing_secret:
        raise TokenValidationError("Authentication is not configured.")

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.auth_jwt_signing_secret,
            algorithms=["HS256"],
            audience=SUPABASE_AUDIENCE,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenValidationError(str(exc)) from exc

    subject = payload.get("sub")
    if not subject:
        raise TokenValidationError("Token is missing a subject claim.")

    return AccessTokenClaims(
        auth_user_id=subject,
        email=payload.get("email"),
        session_id=payload.get("session_id"),
        issued_at=payload.get("iat"),
        expires_at=payload.get("exp"),
    )
