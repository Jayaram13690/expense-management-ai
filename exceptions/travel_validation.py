"""
Travel Validation Exception.

Raised by TravelValidationService when pre-submission travel
validation fails.  Inherits from ApplicationException so that all
existing error-handling infrastructure (serialisation, logging,
HTTP mapping) works without changes.
"""

from exceptions.base import ApplicationException


class TravelValidationException(ApplicationException):
    """
    Raised when enterprise travel validation fails.

    Separate from the generic ValidationException so that callers
    can distinguish *travel pre-validation* failures from regular
    field-level validation errors.

    Error codes used by TravelValidationService
    --------------------------------------------
    FUTURE_TRIP                 Trip has not started yet.
    ONGOING_TRIP                Trip is still in progress.
    SUBMISSION_WINDOW_EXPIRED   Claim submitted after the deadline.
    EXISTING_DRAFT              An active draft already exists.
    OVERLAPPING_TRIP            Dates overlap an existing claim.
    EXPENSE_DATE_OUT_OF_RANGE   An expense date falls outside the trip.
    """

    pass
