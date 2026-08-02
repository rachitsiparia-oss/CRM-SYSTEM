"""Idempotent development seed data — one `Integration` row per real
integration point the codebase actually has an adapter for (Phase 10's
communication channels, Phase 14's AI providers, Supabase Auth/Storage,
the primary database, Sentry). This mirrors
INTEGRATION_CATEGORIES exactly once each; no row is seeded for a category
this codebase does not yet implement (POS, payments, delivery platforms
— CLAUDE.md section 24 forbids "fake integrations or placeholder data that
appears production-ready"). `status`/`health_state` are left at their
model defaults (`draft`/`unknown`) — `app.integrations.health.run_health_checks`
is what actually determines real status, not this seed.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Integration, StaffUser

_INTEGRATIONS: tuple[tuple[str, str, str, str], ...] = (
    # code, category, provider_code, display_name
    ("whatsapp_channel", "whatsapp", "whatsapp", "WhatsApp (Communication Channel)"),
    ("sms_channel", "sms", "sms", "SMS (Communication Channel)"),
    ("email_channel", "email", "email", "Email (Communication Channel)"),
    ("ai_openai", "ai_provider", "openai", "OpenAI (Controlled AI)"),
    ("ai_groq", "ai_provider", "groq", "Groq (Controlled AI)"),
    ("ai_mock", "ai_provider", "mock", "Mock AI Provider (fallback)"),
    ("primary_database", "database_storage", "postgres", "Primary PostgreSQL Database"),
    ("supabase_auth", "authentication_identity", "supabase_auth", "Supabase Auth"),
    ("supabase_storage", "file_storage_exports", "supabase_storage", "Supabase Storage"),
    ("sentry", "analytics_observability", "sentry", "Sentry Error Tracking"),
)


async def seed_integrations(session: AsyncSession) -> None:
    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    if actor is None:
        return

    environment = get_settings().environment
    for code, category, provider_code, display_name in _INTEGRATIONS:
        existing = await session.scalar(select(Integration).where(Integration.code == code))
        if existing is not None:
            continue
        session.add(
            Integration(
                code=code,
                category=category,
                provider_code=provider_code,
                display_name=display_name,
                environment=environment,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
    await session.flush()
