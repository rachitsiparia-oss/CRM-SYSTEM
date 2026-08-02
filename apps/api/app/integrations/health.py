"""Integration health checks — INTEGRATIONS_AUTOMATIONS_REALTIME.md
section 23.2's health signals, applied per integration `code`. No live
network probe is made against OpenAI/Groq/WhatsApp/etc — an actual call
would cost money and risk rate limits for a background health tick, so
"healthy" here means "correctly configured and reachable in principle"
(a credential is present, the underlying channel/database is enabled and
connectable), matching this project's already-established
`get_ai_provider()`/mock-fallback pattern rather than inventing a second
kind of liveness probe.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import CommunicationChannel, Integration
from app.integrations.service import list_integrations, record_health_result


async def _check_ai_provider(integration: Integration) -> bool:
    settings = get_settings()
    if integration.provider_code == "openai":
        return bool(settings.openai_api_key)
    if integration.provider_code == "groq":
        return bool(settings.groq_api_key)
    return True  # "mock" is always healthy — it's the deliberate fallback


async def _check_communication_channel(session: AsyncSession, integration: Integration) -> bool:
    channel = await session.scalar(
        select(CommunicationChannel).where(CommunicationChannel.code == integration.provider_code)
    )
    return channel is not None and channel.is_enabled


async def _check_database(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_supabase_config() -> bool:
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_service_role_key)


async def run_health_checks(session: AsyncSession) -> dict[str, int]:
    counts = {"healthy": 0, "unhealthy": 0}
    for integration in await list_integrations(session):
        if integration.category == "ai_provider":
            healthy = await _check_ai_provider(integration)
        elif integration.category in ("whatsapp", "sms", "email"):
            healthy = await _check_communication_channel(session, integration)
        elif integration.category == "database_storage":
            healthy = await _check_database(session)
        elif integration.category == "authentication_identity":
            healthy = await _check_supabase_config()
        else:
            continue

        await record_health_result(
            session,
            integration=integration,
            healthy=healthy,
            error_category=None if healthy else "not_configured",
        )
        counts["healthy" if healthy else "unhealthy"] += 1
    return counts
