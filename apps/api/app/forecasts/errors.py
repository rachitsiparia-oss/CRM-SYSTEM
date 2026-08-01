from fastapi import status


class ForecastError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "forecast_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
