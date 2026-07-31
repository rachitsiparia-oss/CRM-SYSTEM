from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.communications.router import router as communications_router
from app.core.asyncio_policy import configure_event_loop_policy
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.observability import configure_sentry
from app.core.request_context import RequestContextMiddleware
from app.customers.router import router as customers_router
from app.health.router import router as health_router
from app.inventory.router import router as inventory_router
from app.knowledge.router import router as knowledge_router
from app.leads.router import router as leads_router
from app.loyalty.router import router as loyalty_router
from app.menu.router import router as menu_router
from app.notifications.router import router as notifications_router
from app.orders.router import router as orders_router
from app.reservations.router import router as reservations_router
from app.roles.router import router as roles_router
from app.segments.router import router as segments_router
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

    return app


app = create_app()
