"""Gift card code/PIN generation, hashing, and masking —
GROWTH_AND_INTELLIGENCE.md section 9.6. The plaintext code is generated
here, returned to the caller exactly once (at issue time), and never
persisted — only `code_hash`/`code_last4` are stored.
"""

from __future__ import annotations

import re
import secrets

from app.core.hashing import hash_secret, verify_secret

_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O/1/I — avoids misread codes
_CODE_LENGTH = 16
_CODE_GROUP_SIZE = 4
_NON_ALNUM = re.compile(r"[^0-9A-Za-z]")


def generate_card_number() -> str:
    return f"GC-{secrets.token_hex(6).upper()}"


def generate_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


def format_code_display(code: str) -> str:
    groups = [code[i : i + _CODE_GROUP_SIZE] for i in range(0, len(code), _CODE_GROUP_SIZE)]
    return "-".join(groups)


def normalize_code_input(raw: str) -> str:
    """Strips the dashes/whitespace `format_code_display` adds and
    uppercases — the code is issued to the caller in its grouped display
    form (section 9.3's "masked display form"), so redemption must accept
    that same form back, not only the raw ungrouped string. Hashing and
    verification always operate on this normalized form."""
    return _NON_ALNUM.sub("", raw).upper()


def masked_display(code_last4: str) -> str:
    return f"****-****-****-{code_last4}"


def hash_code(code: str) -> str:
    return hash_secret(normalize_code_input(code))


def verify_code(code: str, code_hash: str) -> bool:
    return verify_secret(normalize_code_input(code), code_hash)


def hash_pin(pin: str) -> str:
    return hash_secret(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    return verify_secret(pin, pin_hash)
