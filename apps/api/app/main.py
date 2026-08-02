from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.achievements.router import router as achievements_router
from app.anomalies.router import router as anomalies_router
from app.auth.router import router as auth_router
from app.cache.router import router as cache_router
from app.campaigns.router import router as campaigns_router
from app.commercial_risk.router import router as commercial_risk_router
from app.communications.router import router as communications_router
from app.complaints.router import router as complaints_router
from app.controlled_ai.router import router as controlled_ai_router
from app.core.asyncio_policy import configure_event_loop_policy
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.metrics_middleware import MetricsMiddleware
from app.core.observability import configure_sentry
from app.core.request_context import RequestContextMiddleware
from app.customer_credit.router import router as customer_credit_router
from app.customers.router import router as customers_router
from app.dead_letter.router import router as dead_letter_router
from app.event_bus.router import router as event_log_router
from app.feature_flags.router import router as feature_flags_router
from app.feedback.router import review_requests_router
from app.feedback.router import router as feedback_router
from app.forecasts.router import router as forecasts_router
from app.gift_cards.router import router as gift_cards_router
from app.health.router import router as health_router
from app.integrations.router import router as integrations_router
from app.inventory.router import router as inventory_router
from app.jobs.router import router as jobs_router
from app.jobs.router import scheduler_router
from app.knowledge.router import router as knowledge_router
from app.leads.router import router as leads_router
from app.loyalty.router import router as loyalty_router
from app.menu.router import router as menu_router
from app.notifications.router import router as notifications_router
from app.offers.router import router as offers_router
from app.operational_settings.router import router as operational_settings_router
from app.orders.router import router as orders_router
from app.referrals.router import router as referrals_router
from app.report_exports.router import router as report_exports_router
from app.report_schedules.router import router as report_schedules_router
from app.reports.router import router as reports_router
from app.reservations.router import router as reservations_router
from app.roles.router import router as roles_router
from app.segments.router import router as segments_router
from app.service_recovery.router import router as service_recovery_router
from app.staff.router import router as staff_router
from app.staff_operations.router import router as staff_operations_router
from app.tasks.router import router as tasks_router

# Must run before uvicorn (or anything else) creates an event loop — see
# app/core/asyncio_policy.py.
configure_event_loop_policy()

logger = get_logger(__name__)


def _lifespan_factory(
    settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("api_startup", environment=settings.environment)
        yield
        logger.info("api_shutdown", environment=settings.environment)

    return lifespan


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    configure_sentry(settings)

    app = FastAPI(
        title="RKPR Restaurant CRM API",
        version="0.1.0",
        # Public API is versioned under /api/v1 — DATABASE_AND_API.md
        # section 19.1. Health endpoints stay unversioned and unauthenticated.
        lifespan=_lifespan_factory(settings),
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(staff_router)
    app.include_router(roles_router)
    app.include_router(customers_router)
    app.include_router(leads_router)
    app.include_router(menu_router)
    app.include_router(orders_router)
    app.include_router(inventory_router)
    app.include_router(reservations_router)
    app.include_router(communications_router)
    app.include_router(tasks_router)
    app.include_router(notifications_router)
    app.include_router(knowledge_router)
    app.include_router(staff_operations_router)
    app.include_router(loyalty_router)
    app.include_router(segments_router)
    app.include_router(offers_router)
    app.include_router(campaigns_router)
    app.include_router(referrals_router)
    app.include_router(customer_credit_router)
    app.include_router(achievements_router)
    app.include_router(gift_cards_router)
    app.include_router(commercial_risk_router)
    app.include_router(feedback_router)
    app.include_router(review_requests_router)
    app.include_router(complaints_router)
    app.include_router(service_recovery_router)
    app.include_router(reports_router)
    app.include_router(report_exports_router)
    app.include_router(report_schedules_router)
    app.include_router(anomalies_router)
    app.include_router(forecasts_router)
    app.include_router(controlled_ai_router)
    app.include_router(jobs_router)
    app.include_router(scheduler_router)
    app.include_router(dead_letter_router)
    app.include_router(integrations_router)
    app.include_router(feature_flags_router)
    app.include_router(operational_settings_router)
    app.include_router(event_log_router)
    app.include_router(cache_router)

    return app


app = create_app()
