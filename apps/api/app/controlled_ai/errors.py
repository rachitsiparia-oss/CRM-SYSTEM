from fastapi import status


class ControlledAiError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "controlled_ai_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedFeatureError(ControlledAiError):
    code = "unsupported_feature"


class HrSensitiveDataBlockedError(ControlledAiError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "hr_sensitive_data_blocked"


class ProviderUnavailableError(ControlledAiError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ai_provider_unavailable"
