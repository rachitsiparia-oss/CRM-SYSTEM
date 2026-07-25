"""One-time CLI to link the first real Supabase Auth user to the `owner`
role, breaking Phase 3's bootstrap chicken-and-egg problem (every other
staff account is created via the invitation workflow, which requires an
already-privileged inviter to exist).

Usage — after creating the owner's account in Supabase Auth (dashboard or
`supabase.auth.admin.createUser`) and copying their auth user UUID:

    uv run --package rkpr-api python -m app.db.bootstrap_owner \\
        --auth-user-id <uuid> --email owner@example.com \\
        --first-name Rohan --last-name Prakash

Safe to rerun: if a staff_user already exists for the given auth_user_id,
it is reported and left unchanged.
"""

import argparse
import asyncio
import uuid

from app.core.asyncio_policy import configure_event_loop_policy
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import get_session_factory
from app.permissions.seed import bootstrap_owner

logger = get_logger(__name__)


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not set.")

    session_factory = get_session_factory()
    async with session_factory() as session:
        staff_user = await bootstrap_owner(
            session,
            auth_user_id=args.auth_user_id,
            email=args.email,
            first_name=args.first_name,
            last_name=args.last_name,
            employee_code=args.employee_code,
        )
        await session.commit()

    logger.info(
        "owner_bootstrapped",
        staff_user_id=str(staff_user.id),
        auth_user_id=str(staff_user.auth_user_id),
        email=staff_user.email,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-user-id", type=uuid.UUID, required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--employee-code", default="EMP-0001")
    args = parser.parse_args()

    configure_event_loop_policy()
    settings = get_settings()
    configure_logging(settings)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
