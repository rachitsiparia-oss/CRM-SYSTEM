"""Mints a real HS256 access token for k6 load-test scripts to authenticate
with, using the exact same signing logic
`apps/api/tests/conftest.py::make_access_token` uses for the pytest suite —
this is not a separate/weaker auth path, it exercises the real verification
code in `app.auth.tokens`.

Requires AUTH_JWT_SIGNING_SECRET to be set in the target environment's
apps/api/.env (or exported directly) and a real `auth_user_id` from a
StaffUser row that already exists in that environment's database — this
script does not create one. For local/CI environments seeded via
`app.db.seed`, query for a seeded staff user's `auth_user_id` first, e.g.:

    SELECT auth_user_id FROM staff_users WHERE email = 'owner@rkpr.test';

Usage:
    cd apps/api
    uv run python ../../tests/load/mint_token.py --auth-user-id <uuid> [--email owner@rkpr.test]

Then pass the printed token to k6:
    k6 run -e ACCESS_TOKEN=$(uv run python ../../tests/load/mint_token.py --auth-user-id <uuid>) \\
        tests/load/api_smoke.js
"""

import argparse
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

import jwt  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-user-id", required=True, help="A real StaffUser.auth_user_id")
    parser.add_argument("--email", default=None)
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    args = parser.parse_args()

    settings = get_settings()
    if not settings.auth_jwt_signing_secret:
        raise SystemExit(
            "AUTH_JWT_SIGNING_SECRET is not configured for this environment — "
            "set it in apps/api/.env or export it before running this script."
        )

    now = int(time.time())
    payload = {
        "sub": str(uuid.UUID(args.auth_user_id)),
        "aud": "authenticated",
        "iat": now,
        "exp": now + args.ttl_seconds,
        "session_id": str(uuid.uuid4()),
    }
    if args.email:
        payload["email"] = args.email

    token = jwt.encode(payload, settings.auth_jwt_signing_secret, algorithm="HS256")
    print(token)


if __name__ == "__main__":
    main()
