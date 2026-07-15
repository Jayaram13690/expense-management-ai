"""
Travel Validation Service.

Enterprise travel pre-validation engine for the Expense Management System.

Responsibilities
----------------
This service validates the *travel itself* before any downstream
processing (employee validation, policy calculation, duplicate detection,
or claim creation) runs.

It mirrors the behaviour of enterprise expense systems such as
SAP Concur, Oracle Expenses, and Workday Expenses, which gate the
expense workflow behind a travel validation layer.

Validation sequence (fail-fast — stops at first failure)
---------------------------------------------------------
1. Future Trip       — trip has not started yet, reject submission.
2. Ongoing Trip      — trip is still in progress, reject submission.
3. Submission Window — claim missed the configurable deadline.
4. Existing Draft    — a DRAFT claim already exists for this trip;
                        resume it instead of creating a new one.
5. Overlapping Trip  — dates overlap an existing active claim.
6. Expense Dates     — every expense item must fall within the trip.

Configuration
-------------
``CLAIM_SUBMISSION_WINDOW_DAYS`` in TravelValidationConfig controls
how many days after trip completion a claim can be submitted.  The
default is 7 days.  This value is intentionally kept in one place so
that a future move to a company-policy table only requires updating
this constant.

Integration
-----------
Call ``validate_before_submission()`` from ExpenseClaimService (or any
caller that creates/previews a claim) *before* employee validation,
policy calculation, and duplicate detection.

    from services.travel_validation_service import TravelValidationService

    travel_service = TravelValidationService(claim_repository)
    travel_service.validate_before_submission(
        employee_id=request.employee_id,
        trip_start_date=request.trip_start_date,
        trip_end_date=request.trip_end_date,
        expense_items=request.expense_items,
    )

The method raises ``TravelValidationException`` on any failure so that
callers do not need to inspect return values — a return means all
checks passed.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from config.enums import ClaimStatus
from exceptions.travel_validation import TravelValidationException
from models.dto.expense_item import ExpenseItem
from models.expense_claim import ExpenseClaim
from repositories.expense_claim_repository import ExpenseClaimRepository
from services.base import BaseService

if TYPE_CHECKING:
    pass


###############################################################################
# Configurable constants
###############################################################################


class TravelValidationConfig:
    """
    Configurable constants for the Travel Validation Engine.

    Centralising these values here means a future migration to a
    company-policy table only requires changing this one class.

    Attributes
    ----------
    CLAIM_SUBMISSION_WINDOW_DAYS:
        Maximum number of calendar days after ``trip_end_date`` within
        which a travel expense claim must be submitted.

        Company policy: claims must be submitted within 7 days of
        travel completion.  This default can be overridden by passing
        a custom value to ``TravelValidationService``.
    """

    CLAIM_SUBMISSION_WINDOW_DAYS: int = 7


###############################################################################
# Statuses that are excluded from overlap / draft detection
###############################################################################

#: Claims in these statuses are ignored when searching for overlapping
#: or draft claims.  A REJECTED or CANCELLED claim no longer represents
#: an active travel period.
_EXCLUDED_STATUSES: frozenset[ClaimStatus] = frozenset(
    {
        ClaimStatus.REJECTED,
        ClaimStatus.CLOSED,
    }
)

#: Statuses that represent an active draft that the employee should
#: resume rather than create another claim for.
_DRAFT_STATUSES: frozenset[ClaimStatus] = frozenset(
    {
        ClaimStatus.DRAFT,
    }
)


###############################################################################
# TravelValidationService
###############################################################################


class TravelValidationService(BaseService):
    """
    Enterprise Travel Validation Engine.

    Validates the *travel itself* before any downstream expense
    processing runs.  All six validations are executed in the order
    mandated by the task specification (fail-fast).

    Parameters
    ----------
    claim_repository:
        Repository used to query existing employee claims.  Injected
        so that unit tests can substitute a fake repository without
        touching the database.

    submission_window_days:
        Maximum days after trip completion within which a claim must
        be submitted.  Defaults to ``TravelValidationConfig.CLAIM_SUBMISSION_WINDOW_DAYS``.
    """

    def __init__(
        self,
        claim_repository: ExpenseClaimRepository | None = None,
        *,
        submission_window_days: int | None = None,
    ) -> None:
        super().__init__()
        self.claim_repository: ExpenseClaimRepository = claim_repository or ExpenseClaimRepository()
        self.submission_window_days: int = (
            submission_window_days
            if submission_window_days is not None
            else TravelValidationConfig.CLAIM_SUBMISSION_WINDOW_DAYS
        )

    ###########################################################################
    # Public API
    ###########################################################################

    def validate_before_submission(
        self,
        *,
        employee_id: str,
        trip_start_date: date,
        trip_end_date: date,
        expense_items: list[ExpenseItem],
        today: date | None = None,
    ) -> None:
        """
        Run all six travel validations in the mandated order.

        Raises ``TravelValidationException`` on the *first* validation
        that fails.  A clean return means all checks passed and the
        claim may proceed to employee validation, policy calculation,
        and duplicate detection.

        Parameters
        ----------
        employee_id:
            Employee submitting the claim.

        trip_start_date:
            First day of the business trip.

        trip_end_date:
            Last day of the business trip.

        expense_items:
            Expense line items from the submission request.

        today:
            Override for the current date (used in tests).  Defaults
            to ``date.today()``.

        Raises
        ------
        TravelValidationException
            If any validation fails.
        """
        self.log_start("Travel Validation")
        self.logger.info(
            "Travel Validation Started — employee_id=%s trip=%s→%s",
            employee_id,
            trip_start_date,
            trip_end_date,
        )

        current_date: date = today or date.today()

        # 1. Future trip
        self._validate_future_trip(trip_start_date, current_date)

        # 2. Ongoing trip
        self._validate_ongoing_trip(trip_end_date, current_date)

        # 3. Submission window
        self._validate_submission_window(trip_end_date, current_date)

        # Retrieve employee claims once for validations 4 and 5
        employee_claims = self._get_active_employee_claims(employee_id)

        # 4. Existing draft
        self._validate_existing_draft(employee_claims, trip_start_date, trip_end_date)

        # 5. Overlapping trip
        self._validate_overlapping_trip(employee_claims, trip_start_date, trip_end_date)

        # 6. Expense date bounds
        self._validate_expense_dates(expense_items, trip_start_date, trip_end_date)

        self.logger.info(
            "Travel Validation Completed — all checks passed for employee_id=%s",
            employee_id,
        )
        self.log_success("Travel Validation")

    ###########################################################################
    # Validation 1 — Future Trip
    ###########################################################################

    def _validate_future_trip(
        self,
        trip_start_date: date,
        current_date: date,
    ) -> None:
        """
        Reject submissions where the trip has not yet started.

        Condition: current_date < trip_start_date

        Raises
        ------
        TravelValidationException
            If the trip is in the future.
        """
        if current_date < trip_start_date:
            self.logger.warning(
                "Future Trip Validation Failed — current_date=%s trip_start=%s",
                current_date,
                trip_start_date,
            )
            raise TravelValidationException(
                message=(
                    "Expense claims cannot be submitted before travel begins. "
                    f"Your trip starts on {trip_start_date}. "
                    "You may save a draft and submit after your trip has started."
                ),
                error_code="FUTURE_TRIP",
                metadata={
                    "current_date": str(current_date),
                    "trip_start_date": str(trip_start_date),
                },
            )

        self.logger.info(
            "Future Trip Validation Passed — trip_start=%s current_date=%s",
            trip_start_date,
            current_date,
        )

    ###########################################################################
    # Validation 2 — Ongoing Trip
    ###########################################################################

    def _validate_ongoing_trip(
        self,
        trip_end_date: date,
        current_date: date,
    ) -> None:
        """
        Reject submissions where the trip is still in progress.

        Condition: current_date < trip_end_date

        Raises
        ------
        TravelValidationException
            If the trip has not yet ended.
        """
        if current_date < trip_end_date:
            self.logger.warning(
                "Ongoing Trip Validation Failed — current_date=%s trip_end=%s",
                current_date,
                trip_end_date,
            )
            raise TravelValidationException(
                message=(
                    "Your trip is still in progress. "
                    "Expense claims can only be submitted after travel has been completed. "
                    f"Your trip ends on {trip_end_date}. "
                    "You may save a draft and submit once your trip is complete."
                ),
                error_code="ONGOING_TRIP",
                metadata={
                    "current_date": str(current_date),
                    "trip_end_date": str(trip_end_date),
                },
            )

        self.logger.info(
            "Ongoing Trip Validation Passed — trip_end=%s current_date=%s",
            trip_end_date,
            current_date,
        )

    ###########################################################################
    # Validation 3 — Submission Window
    ###########################################################################

    def _validate_submission_window(
        self,
        trip_end_date: date,
        current_date: date,
    ) -> None:
        """
        Reject submissions made after the configurable deadline.

        Company policy: claims must be submitted within
        ``self.submission_window_days`` calendar days after
        ``trip_end_date``.

        Condition: current_date > trip_end_date + submission_window_days

        Raises
        ------
        TravelValidationException
            If the submission deadline has passed.
        """
        submission_deadline: date = trip_end_date + timedelta(days=self.submission_window_days)

        if current_date > submission_deadline:
            self.logger.warning(
                "Submission Window Failed — trip_end=%s deadline=%s current_date=%s",
                trip_end_date,
                submission_deadline,
                current_date,
            )
            raise TravelValidationException(
                message=(
                    "This claim cannot be submitted. "
                    f"Company policy requires travel expense claims to be submitted "
                    f"within {self.submission_window_days} days after travel completion.\n"
                    f"Travel End Date:      {trip_end_date}\n"
                    f"Submission Deadline:  {submission_deadline}\n"
                    f"Current Date:         {current_date}"
                ),
                error_code="SUBMISSION_WINDOW_EXPIRED",
                metadata={
                    "trip_end_date": str(trip_end_date),
                    "submission_deadline": str(submission_deadline),
                    "current_date": str(current_date),
                    "submission_window_days": self.submission_window_days,
                },
            )

        self.logger.info(
            "Submission Window Passed — deadline=%s current_date=%s",
            submission_deadline,
            current_date,
        )

    ###########################################################################
    # Validation 4 — Existing Draft
    ###########################################################################

    def _validate_existing_draft(
        self,
        employee_claims: list[ExpenseClaim],
        trip_start_date: date,
        trip_end_date: date,
    ) -> None:
        """
        Resume an existing DRAFT claim instead of creating a duplicate.

        Searches active claims for a DRAFT whose trip period exactly
        matches the new request.  If found, raises
        ``TravelValidationException`` with error_code ``EXISTING_DRAFT``
        and metadata pointing to the existing draft so the caller (or
        the conversational agent) can guide the employee to resume it.

        Raises
        ------
        TravelValidationException
            If a DRAFT claim already exists for the exact same trip period.
        """
        for claim in employee_claims:
            if claim.status not in _DRAFT_STATUSES:
                continue
            if claim.trip_start_date == trip_start_date and claim.trip_end_date == trip_end_date:
                self.logger.info(
                    "Existing Draft Detected — claim_id=%s trip=%s→%s",
                    claim.claim_id,
                    claim.trip_start_date,
                    claim.trip_end_date,
                )
                raise TravelValidationException(
                    message=(
                        f"An existing draft claim was found for this trip "
                        f"({trip_start_date} to {trip_end_date}). "
                        f"Resuming your previous draft. "
                        f"Existing Draft Claim ID: {claim.claim_id}"
                    ),
                    error_code="EXISTING_DRAFT",
                    recoverable=True,
                    metadata={
                        "existing_claim_id": claim.claim_id,
                        "trip_start_date": str(trip_start_date),
                        "trip_end_date": str(trip_end_date),
                        "existing_claim_status": claim.status,
                    },
                )

        self.logger.info(
            "Existing Draft Validation Passed — no draft found for trip=%s→%s",
            trip_start_date,
            trip_end_date,
        )

    ###########################################################################
    # Validation 5 — Overlapping Trip
    ###########################################################################

    def _validate_overlapping_trip(
        self,
        employee_claims: list[ExpenseClaim],
        new_start: date,
        new_end: date,
    ) -> None:
        """
        Reject a new claim whose dates overlap an existing active claim.

        Interval overlap condition (Allen's interval algebra):
            existing_start <= new_end  AND  existing_end >= new_start

        Ignores claims in REJECTED or CLOSED status.

        Raises
        ------
        TravelValidationException
            If an overlapping active claim is found.
        """
        for claim in employee_claims:
            if claim.status in _EXCLUDED_STATUSES:
                continue

            # Draft claims for the exact same trip are handled in validation 4.
            # Here we look for *any* non-excluded claim whose period overlaps.
            if claim.trip_start_date <= new_end and claim.trip_end_date >= new_start:
                self.logger.warning(
                    "Overlapping Claim Detected — existing_claim_id=%s existing=%s→%s new=%s→%s",
                    claim.claim_id,
                    claim.trip_start_date,
                    claim.trip_end_date,
                    new_start,
                    new_end,
                )
                raise TravelValidationException(
                    message=(
                        "A travel expense claim already exists for this travel period. "
                        f"Existing Claim: {claim.claim_id} | "
                        f"Travel Dates: {claim.trip_start_date} to {claim.trip_end_date}. "
                        "Please review the existing claim instead of creating another claim."
                    ),
                    error_code="OVERLAPPING_TRIP",
                    metadata={
                        "existing_claim_id": claim.claim_id,
                        "existing_trip_start": str(claim.trip_start_date),
                        "existing_trip_end": str(claim.trip_end_date),
                        "new_trip_start": str(new_start),
                        "new_trip_end": str(new_end),
                        "existing_claim_status": claim.status,
                    },
                )

        self.logger.info(
            "Overlapping Trip Validation Passed — no overlap for trip=%s→%s",
            new_start,
            new_end,
        )

    ###########################################################################
    # Validation 6 — Expense Date Bounds
    ###########################################################################

    def _validate_expense_dates(
        self,
        expense_items: list[ExpenseItem],
        trip_start_date: date,
        trip_end_date: date,
    ) -> None:
        """
        Ensure every expense item falls within the declared trip period.

        Condition (inclusive): trip_start_date <= expense_date <= trip_end_date

        Raises
        ------
        TravelValidationException
            If any expense date falls outside the trip period.
        """
        for item in expense_items:
            if item.expense_date < trip_start_date or item.expense_date > trip_end_date:
                self.logger.warning(
                    "Expense Date Out of Range — expense_date=%s trip=%s→%s category=%s",
                    item.expense_date,
                    trip_start_date,
                    trip_end_date,
                    item.category_code,
                )
                raise TravelValidationException(
                    message=(
                        f"Expense dated {item.expense_date} falls outside the travel period "
                        f"of {trip_start_date} to {trip_end_date}. "
                        f"Category: {item.category_code}."
                    ),
                    error_code="EXPENSE_DATE_OUT_OF_RANGE",
                    metadata={
                        "expense_date": str(item.expense_date),
                        "category_code": item.category_code,
                        "trip_start_date": str(trip_start_date),
                        "trip_end_date": str(trip_end_date),
                    },
                )

        self.logger.info(
            "Expense Date Validation Passed — all %d items within trip=%s→%s",
            len(expense_items),
            trip_start_date,
            trip_end_date,
        )

    ###########################################################################
    # Internal helpers
    ###########################################################################

    def _get_active_employee_claims(
        self,
        employee_id: str,
    ) -> list[ExpenseClaim]:
        """
        Retrieve all claims for an employee, swallowing unexpected errors.

        If the repository call fails for any reason, we log the error and
        return an empty list so that a transient backend failure does not
        block claim submission.  The duplicate / overlap checks will be
        less reliable, but the system stays available.

        Returns
        -------
        list[ExpenseClaim]
            All known claims for the employee, or an empty list on error.
        """
        try:
            return self.claim_repository.list_employee_claims(employee_id)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "Failed to retrieve employee claims for employee_id=%s: %s",
                employee_id,
                exc,
            )
            return []
