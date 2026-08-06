import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.logging import get_logger
from app.core.metrics import http_request_duration_seconds, http_requests_total

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records `crm_http_request*` for every request. Uses the matched
    route's path template (e.g. `/api/v1/customers/{customer_id}`), not the
    raw URL, so per-record IDs never explode the metric's label
    cardinality.

    Also logs a structured `slow_request` warning for any request over
    `settings.slow_request_threshold_ms` — CLAUDE.md section 19's "slow
    endpoints must be observable" — independent of and in addition to the
    histogram, which requires a scraper computing percentiles to notice an
    outlier; the log line is greppable immediately.
    """

    def __init__(self, app: ASGIApp, *, slow_request_threshold_ms: int) -> None:
        super().__init__(app)
        self._threshold_seconds = slow_request_threshold_ms / 1000

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        labels = {
            "method": request.method,
            "route": route_path,
            "status": str(response.status_code),
        }
        http_request_duration_seconds.labels(**labels).observe(duration)
        http_requests_total.labels(**labels).inc()

        if self._threshold_seconds > 0 and duration >= self._threshold_seconds:
            logger.warning(
                "slow_request",
                method=request.method,
                route=route_path,
                status=response.status_code,
                duration_ms=round(duration * 1000, 1),
            )
        return response
