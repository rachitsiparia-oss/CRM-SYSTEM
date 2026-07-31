"""Salted, keyed-stretched hashing for secrets that must be verifiable
but never stored or logged in plaintext — gift card codes, gift card
PINs (DATABASE_AND_API.md/GROWTH_AND_INTELLIGENCE.md section 9.3).

Staff authentication itself is delegated entirely to Supabase Auth
(CLAUDE.md section 6.1), so this repository has never needed a general
password-hashing utility before now. PBKDF2-HMAC-SHA256 is used rather
than adding a new third-party dependency (bcrypt/argon2) for what is a
narrow, low-volume verification path — CLAUDE.md section 9's "check
whether the capability already exists" before adding a dependency.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


def hash_secret(raw: str) -> str:
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt}${digest.hex()}"


def verify_secret(raw: str, hashed: str) -> bool:
    try:
        algorithm, iterations_str, salt, digest_hex = hashed.split("$", 3)
    except ValueError:
        return False
    if algorithm != _ALGORITHM:
        return False
    try:
        iterations = int(iterations_str)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), iterations)
    return hmac.compare_digest(candidate.hex(), digest_hex)
