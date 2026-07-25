from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.observability import configure_sentry
from app.core.request_context import RequestContextMiddleware
from app.health.router import router as health_router

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

    return app


app = create_app()
