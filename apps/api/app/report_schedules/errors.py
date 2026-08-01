from fastapi import status


class ReportScheduleError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "report_schedule_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NoRecipientsError(ReportScheduleError):
    code = "no_recipients"


class ScheduleOwnerLacksPermissionError(ReportScheduleError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "schedule_owner_lacks_permission"
