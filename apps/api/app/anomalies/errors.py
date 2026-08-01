from fastapi import status


class AnomalyError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "anomaly_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidAnomalyTransitionError(AnomalyError):
    code = "invalid_anomaly_transition"
