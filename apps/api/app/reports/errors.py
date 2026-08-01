"""Typed report domain errors — same shape as app.complaints.errors."""

from fastapi import status


class ReportError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "report_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidMetricSelectionError(ReportError):
    code = "invalid_metric_selection"


class InvalidWindowSelectionError(ReportError):
    code = "invalid_window_selection"


class ReportDefinitionNotEditableError(ReportError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "report_definition_not_editable"


class MetricPermissionDeniedForReportError(ReportError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "metric_permission_denied"
