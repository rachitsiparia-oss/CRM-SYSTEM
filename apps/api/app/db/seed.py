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

from app.achievements.seed import seed_achievements
from app.campaigns.seed import seed_campaigns
from app.communications.seed import seed_communications
from app.complaints.seed import seed_complaints
from app.core.asyncio_policy import configure_event_loop_policy
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.customers.seed import seed_customers
from app.db.session import get_session_factory
from app.feedback.seed import seed_feedback
from app.inventory.seed import seed_inventory
from app.knowledge.seed import seed_knowledge_articles
from app.leads.seed import seed_leads
from app.loyalty.seed import seed_loyalty
from app.menu.seed import seed_menu
from app.offers.seed import seed_offers
from app.orders.seed import seed_orders
from app.permissions.seed import (
    seed_departments,
    seed_permissions,
    seed_role_permissions,
    seed_roles,
)
from app.referrals.seed import seed_referrals
from app.reservations.seed import seed_reservations
from app.segments.seed import seed_segments
from app.service_recovery.seed import seed_service_recovery
from app.staff_operations.seed import seed_staff_operations

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
        await seed_reservations(session)
        await seed_communications(session)
        await seed_staff_operations(session)
        await seed_knowledge_articles(session)
        await seed_loyalty(session)
        await seed_segments(session)
        await seed_offers(session)
        await seed_referrals(session)
        await seed_achievements(session)
        await seed_campaigns(session)
        # gift_cards/customer_credit/commercial_risk are intentionally not
        # seeded — this phase's own rule against fabricating real-value
        # grants to arbitrary customers or synthetic risk events.
        await seed_feedback(session)
        await seed_complaints(session)
        await seed_service_recovery(session)
        # Future phases append their idempotent seed_*(session) calls here —
        # see PROJECT_PLAN.md section 16 (phase dependency rules).
        await session.commit()

    logger.info(
        "seed_complete",
        note=(
            "departments, roles, permissions, role_permissions, customers, leads, menu, "
            "orders, inventory, reservations, communications, staff operations, knowledge "
            "base, loyalty, segments, offers, referrals, achievements, campaigns, feedback, "
            "complaints, service recovery seeded"
        ),
    )


def main() -> None:
    configure_event_loop_policy()
    settings = get_settings()
    configure_logging(settings)
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
