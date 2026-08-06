"""Security response headers — CLAUDE.md section 6 non-negotiable baseline.

This API is a pure JSON surface for `apps/dashboard`, not an HTML site, so
most headers here are defense-in-depth rather than something the browser
actively enforces against JSON responses. `/docs`/`/redoc` (FastAPI's
built-in Swagger UI / ReDoc) are the one HTML surface this process serves,
and they load their JS/CSS from a CDN — see `app.main.create_app`, which
disables both in `staging`/`production` so this middleware's CSP can stay
uniformly strict everywhere without needing a CDN allowlist.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_STRICT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
# Swagger UI (served only outside staging/production) needs its CDN script/
# style/image sources and inline styles to render.
_DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'; "
    "base-uri 'none'"
)
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Sets CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
    Permissions-Policy, and (staging/production only, since HSTS on a
    non-HTTPS local connection is meaningless and confusing during dev)
    Strict-Transport-Security on every response."""

    def __init__(self, app: ASGIApp, *, hsts_enabled: bool) -> None:
        super().__init__(app)
        self._hsts_enabled = hsts_enabled

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = (
            _DOCS_CSP if request.url.path in _DOCS_PATHS else _STRICT_CSP
        )
        if self._hsts_enabled:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response
