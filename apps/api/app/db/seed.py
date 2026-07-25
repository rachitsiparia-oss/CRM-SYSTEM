"""Canonical development seed-data runner — PROJECT_PLAN.md Phase 2 scope
("Add canonical development seed-data scaffolding... to be populated fully
in later phases as each module's schema lands").

Seed data must exactly match the canonical RKPR fixtures in
PROJECT_PLAN.md (restaurant profile, the 65-person dummy staff set, menu,
inventory, suppliers, customer and lead examples) — DATABASE_AND_API.md
section 38. Seed functions must be idempotent and safe to rerun.

No tables exist yet to seed: staff_users/roles land in Phase 3, the menu
and inventory schema lands in Phase 6/8, customers and leads in Phase 5.
This module intentionally has nothing to do until those phases add their
own `seed_*()` function here.
"""

import asyncio

from app.core.asyncio_policy import configure_event_loop_policy
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import get_session_factory

logger = get_logger(__name__)


async def run_seed() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not set — cannot seed without a database.")
    if settings.environment == "production":
        raise SystemExit("Refusing to run development seed data against a production environment.")

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Future phases append their idempotent seed_*(session) calls here,
        # in dependency order (staff/roles before customers, menu before
        # recipes, etc.) — see PROJECT_PLAN.md section 16 (phase dependency
        # rules).
        await session.commit()

    logger.info("seed_complete", note="no seed data defined yet — see module docstring")


def main() -> None:
    configure_event_loop_policy()
    settings = get_settings()
    configure_logging(settings)
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
