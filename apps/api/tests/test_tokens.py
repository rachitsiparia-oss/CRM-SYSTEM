"""Regression coverage for both Supabase JWT signing modes.

The real bug this guards against: Supabase projects created with "JWT
Signing Keys" enabled (the current default) issue ES256-signed tokens
verified via JWKS, not the legacy shared-secret HS256 tokens
`decode_access_token` originally assumed. A project on that mode made
every request fail with a generic 401 until this was fixed.
"""

import time
import uuid
from unittest.mock import MagicMock, patch

import jwt
import pytest
from app.auth.tokens import TokenValidationError, decode_access_token
from cryptography.hazmat.primitives.asymmetric import ec


def test_decodes_legacy_hs256_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.auth.tokens.get_settings",
        lambda: MagicMock(auth_jwt_signing_secret="test-secret", supabase_url=None),
    )
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "iat": now, "exp": now + 3600},
        "test-secret",
        algorithm="HS256",
    )

    claims = decode_access_token(token)
    assert claims.auth_user_id


def test_decodes_jwks_es256_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mints a real ES256 token with a locally-generated key, standing in
    for Supabase's asymmetric JWT Signing Keys mode, and verifies it
    through the same JWKS code path used against the live Supabase
    project (only the key-fetching step is stubbed; the actual
    cryptographic verification in jwt.decode is not)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    subject = str(uuid.uuid4())
    now = int(time.time())
    token = jwt.encode(
        {"sub": subject, "aud": "authenticated", "iat": now, "exp": now + 3600},
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key-id"},
    )

    monkeypatch.setattr(
        "app.auth.tokens.get_settings",
        lambda: MagicMock(supabase_url="https://example.supabase.co", auth_jwt_signing_secret=None),
    )

    fake_signing_key = MagicMock()
    fake_signing_key.key = private_key.public_key()
    fake_client = MagicMock()
    fake_client.get_signing_key_from_jwt.return_value = fake_signing_key

    with patch("app.auth.tokens._jwks_client", return_value=fake_client):
        claims = decode_access_token(token)

    assert claims.auth_user_id == subject


def test_hs256_token_rejected_when_secret_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.auth.tokens.get_settings",
        lambda: MagicMock(auth_jwt_signing_secret=None, supabase_url=None),
    )
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "iat": now, "exp": now + 3600},
        "whatever",
        algorithm="HS256",
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token)


def test_es256_token_rejected_when_supabase_url_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.auth.tokens.get_settings",
        lambda: MagicMock(auth_jwt_signing_secret=None, supabase_url=None),
    )
    private_key = ec.generate_private_key(ec.SECP256R1())
    now = int(time.time())
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "iat": now, "exp": now + 3600},
        private_key,
        algorithm="ES256",
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token)
