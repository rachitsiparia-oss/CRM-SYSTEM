"""Typed inventory domain errors.

This phase's own instruction requires the API to "return clear domain
errors" for a named list of conditions. Each is a distinct exception here so
the router can map it to a precise HTTP status and message rather than every
stock failure collapsing into a generic 400 — and so service-layer tests can
assert on the specific failure mode instead of matching error strings.

`InventoryError` carries an HTTP status and a stable `code` string. The
router converts these to the project's standard error envelope; nothing here
imports anything from the service layer, so the module stays trivially
importable from both services and tests.
"""

from fastapi import status


class InventoryError(Exception):
    """Base class for every inventory domain failure."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "inventory_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InsufficientStockError(InventoryError):
    code = "insufficient_stock"


class IncompatibleUnitError(InventoryError):
    code = "incompatible_unit"


class MissingConversionError(InventoryError):
    code = "missing_conversion"


class ExpiredBatchError(InventoryError):
    code = "expired_batch"


class NegativeStockNotAllowedError(InventoryError):
    code = "negative_stock_not_allowed"


class AlreadyPostedError(InventoryError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_posted"


class NotPostedError(InventoryError):
    code = "not_posted"


class AlreadyReversedError(InventoryError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_reversed"


class DuplicateIdempotencyKeyError(InventoryError):
    status_code = status.HTTP_409_CONFLICT
    code = "duplicate_idempotency_key"


class StaleVersionError(InventoryError):
    status_code = status.HTTP_409_CONFLICT
    code = "stale_version"


class InvalidCountStateError(InventoryError):
    code = "invalid_count_state"


class MissingRecipeError(InventoryError):
    code = "missing_recipe"


class InactiveRecipeError(InventoryError):
    code = "inactive_recipe"


class ReservationMismatchError(InventoryError):
    status_code = status.HTTP_409_CONFLICT
    code = "reservation_mismatch"


class StockBalanceDriftError(InventoryError):
    status_code = status.HTTP_409_CONFLICT
    code = "stock_balance_drift"


class InvalidLocationError(InventoryError):
    code = "invalid_location"


class BatchRequiredError(InventoryError):
    code = "batch_required"


class ImmutableRecordError(InventoryError):
    status_code = status.HTTP_409_CONFLICT
    code = "immutable_record"
