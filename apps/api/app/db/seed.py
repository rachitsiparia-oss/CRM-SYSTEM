"""Canonical development seed-data runner — PROJECT_PLAN.md Phase 2 scope
("Add canonical development seed-data scaffolding... to be populated fully
in later phases as each module's schema lands").

Seed data must exactly match the canonical RKPR fixtures in
PROJECT_PLAN.md (restaurant profile, the 65-person dummy staff set, menu,
inventory, suppliers, customer and lead examples) — DATABASE_AND_API.md
section 38. Seed functions must be idempotent and safe to rerun.

Phase 3 adds departments, roles, the permission registry, and the default
role-permission matrix. The dummy 65-person staff roster is intentionally
not seeded here: every staff_user must be linked to a real Supabase Auth
identity (`auth_user_id`), and no such identities exist until real accounts
are created. The menu, inventory, customer, and lead schema lands in later
phases and will add their own `seed_*()` calls here.
"""

import asyncio

from app.core.asyncio_policy import configure_event_loop_policy
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.customers.seed import seed_customers
from app.db.session import get_session_factory
from app.inventory.seed import seed_inventory
from app.leads.seed import seed_leads
from app.menu.seed import seed_menu
from app.orders.seed import seed_orders
from app.permissions.seed import (
    seed_departments,
    seed_permissions,
    seed_role_permissions,
    seed_roles,
)

logger = get_logger(__name__)


async def run_seed() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not set — cannot seed without a database.")
    if settings.environment == "production":
        raise SystemExit("Refusing to run development seed data against a production environment.")

    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_departments(session)
        await seed_roles(session)
        await seed_permissions(session)
        await seed_role_permissions(session)
        await seed_customers(session)
        await seed_leads(session)
        await seed_menu(session)
        await seed_orders(session)
        await seed_inventory(session)
        # Future phases append their idempotent seed_*(session) calls here —
        # see PROJECT_PLAN.md section 16 (phase dependency rules).
        await session.commit()

    logger.info(
        "seed_complete",
        note=(
            "departments, roles, permissions, role_permissions, customers, leads, menu, "
            "orders, inventory seeded"
        ),
    )


def main() -> None:
    configure_event_loop_policy()
    settings = get_settings()
    configure_logging(settings)
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
