from typing import Any, Literal

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Stable error categories — DATABASE_AND_API.md section 19.4. Every error
# response uses one of these codes; never leak stack traces or SQL details.
ErrorCode = Literal[
    "validation_error",
    "authentication_required",
    "permission_denied",
    "not_found",
    "conflict",
    "invalid_state_transition",
    "rate_limited",
    "external_dependency_unavailable",
    "integration_configuration_error",
    "retryable_processing_failure",
    "internal_error",
]

_STATUS_TO_CODE: dict[int, ErrorCode] = {
    status.HTTP_400_BAD_REQUEST: "validation_error",
    status.HTTP_401_UNAUTHORIZED: "authentication_required",
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "validation_error",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
}


def _error_body(
    code: ErrorCode,
    message: str,
    request: Request,
    field_errors: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    request_id = request.headers.get("X-Request-ID", "")
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if field_errors:
        body["error"]["field_errors"] = field_errors
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, "internal_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, str(exc.detail), request),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"][1:]) or "__root__"
            field_errors.setdefault(field, []).append(error["msg"])
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body(
                "validation_error",
                "The request could not be processed.",
                request,
                field_errors,
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Never expose the exception message or stack trace to the client —
        # CLAUDE.md section 6.3. Sentry captures the real detail server-side
        # once observability is wired up.
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "internal_error",
                "An unexpected error occurred.",
                request,
            ),
        )
