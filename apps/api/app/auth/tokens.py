"""Supabase Auth access-token verification.

Supabase supports two signing modes and a project may be on either:

- Legacy shared secret: HS256, verified against `AUTH_JWT_SIGNING_SECRET`
  (Project Settings -> API -> JWT Settings -> "Legacy JWT Secret").
- JWT Signing Keys (current default for new projects): ES256/RS256,
  asymmetric, verified against the project's public keys published at
  `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. There is no shared
  secret to configure for this mode -- `AUTH_JWT_SIGNING_SECRET` is simply
  unused when a token arrives in this mode.

Both avoid a network round trip to Supabase on *most* requests
(ARCHITECTURE_AND_TECH_STACK.md section 10.1 step 5, "FastAPI validates
the token"): the JWKS case still needs one fetch, but `PyJWKClient` caches
the keys in-process, so it only refetches when a `kid` it hasn't seen
appears (i.e., on Supabase's own key rotation, not per request).

The token's own (unverified) header `alg` selects which path runs -- this
is safe because the actual cryptographic verification below still fails
closed on a mismatched or forged algorithm; reading `alg` only decides
which key material to verify against, it never skips verification.
"""

from dataclasses import dataclass
from functools import lru_cache
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


@lru_cache
def _jwks_client(jwks_url: str) -> "jwt.PyJWKClient":
    return jwt.PyJWKClient(jwks_url, cache_keys=True)


def _decode_with_jwks(token: str, settings: Any) -> dict[str, Any]:
    if not settings.supabase_url:
        raise TokenValidationError("Authentication is not configured.")
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        payload: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=SUPABASE_AUDIENCE,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenValidationError(str(exc)) from exc
    return payload


def _decode_with_shared_secret(token: str, settings: Any) -> dict[str, Any]:
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
    return payload


def decode_access_token(token: str) -> AccessTokenClaims:
    settings = get_settings()

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise TokenValidationError(str(exc)) from exc

    algorithm = unverified_header.get("alg", "")
    if algorithm.startswith("HS"):
        payload = _decode_with_shared_secret(token, settings)
    else:
        payload = _decode_with_jwks(token, settings)

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
