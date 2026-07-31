"""Typed segment domain errors — same shape as app.loyalty.errors."""

from fastapi import status


class SegmentError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "segment_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DuplicateSegmentCodeError(SegmentError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_segment_code"


class WrongSegmentTypeError(SegmentError):
    code = "wrong_segment_type"


class InvalidRuleDefinitionError(SegmentError):
    code = "invalid_rule_definition"
