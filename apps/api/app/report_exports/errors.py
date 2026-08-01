"""Typed export domain errors — same shape as app.reports.errors."""

from fastapi import status


class ExportError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "export_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedExportFormatError(ExportError):
    code = "unsupported_export_format"


class ExportTooLargeError(ExportError):
    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    code = "export_too_large"


class ExportNotReadyError(ExportError):
    code = "export_not_ready"


class ExportExpiredError(ExportError):
    status_code = status.HTTP_410_GONE
    code = "export_expired"
