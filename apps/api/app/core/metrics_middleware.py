import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import http_request_duration_seconds, http_requests_total


class MetricsMiddleware(BaseHTTPMiddleware):
    """Records `crm_http_request*` for every request. Uses the matched
    route's path template (e.g. `/api/v1/customers/{customer_id}`), not the
    raw URL, so per-record IDs never explode the metric's label
    cardinality."""

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
        return response
