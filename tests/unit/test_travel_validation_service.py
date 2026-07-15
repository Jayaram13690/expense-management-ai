"""
Unit Tests — TravelValidationService.

Tests are fully isolated: no database, no AWS, no network calls.
The ExpenseClaimRepository is replaced with an in-memory fake.

Covered scenarios
-----------------
✓  Future Trip                  — current_date < trip_start_date
✓  Ongoing Trip                 — current_date < trip_end_date
✓  Submission Window (pass)     — current_date <= trip_end + window
✓  Submission Window (fail)     — current_date > trip_end + window
✓  Existing Draft               — DRAFT claim for exact same trip period
✓  Overlapping Trip             — dates intersect an existing active claim
✓  Non-overlapping Trip         — adjacent dates do not trigger overlap
✓  Expense Date Inside Travel   — expense_date within trip period → OK
✓  Expense Date Outside Travel  — expense_date outside trip period → fail

Run with:
    pytest tests/unit/test_travel_validation_service.py -v
"""

from __future__ import annotations

import copy
from datetime import date
from decimal import Decimal

import pytest

from config.enums import ClaimStatus
from exceptions.travel_validation import TravelValidationException
from models.approval import Approval
from models.claim_amount import ClaimAmount
from models.dto.expense_item import ExpenseItem
from models.expense_claim import ExpenseClaim
from services.travel_validation_service import (
    TravelValidationConfig,
    TravelValidationService,
)

###############################################################################
# Fake repository
###############################################################################


class FakeClaimRepository:
    """
    In-memory stub for ExpenseClaimRepository.

    Stores ExpenseClaim instances by claim_id.  Supports only the
    ``list_employee_claims`` method that TravelValidationService calls.
    """

    def __init__(self, claims: list[ExpenseClaim] | None = None) -> None:
        self._claims: list[ExpenseClaim] = list(claims or [])

    def list_employee_claims(self, employee_id: str) -> list[ExpenseClaim]:
        return [copy.deepcopy(c) for c in self._claims if c.employee_id == employee_id]


###############################################################################
# Helpers
###############################################################################

_EMPLOYEE_ID = "EMP0001"

# Reference dates used throughout the test suite
_TRIP_START = date(2026, 7, 1)
_TRIP_END = date(2026, 7, 7)


def _make_expense_item(
    expense_date: date,
    category_code: str = "MEALS",
    amount: Decimal = Decimal("1000"),
) -> ExpenseItem:
    """Return a minimal valid ExpenseItem DTO."""
    return ExpenseItem(
        category_code=category_code,
        description="Test expense item",
        expense_date=expense_date,
        requested_amount=amount,
        currency="INR",
        receipt_available=True,
    )


def _make_claim(
    *,
    trip_start: date = _TRIP_START,
    trip_end: date = _TRIP_END,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    claim_id: str = "CLM000000000001",
    employee_id: str = _EMPLOYEE_ID,
) -> ExpenseClaim:
    """Return a minimal valid ExpenseClaim aggregate for repository seeding."""
    return ExpenseClaim(
        claim_id=claim_id,
        employee_id=employee_id,
        employee_name="Test Employee",
        employee_grade="G5",
        department="Engineering",
        trip_name="Test Trip",
        business_purpose="Business meeting for project planning purposes.",
        destination="Bangalore",
        trip_start_date=trip_start,
        trip_end_date=trip_end,
        status=status,
        amount=ClaimAmount(
            claimed_amount=Decimal("5000"),
            approved_amount=Decimal("5000"),
            reimbursable_amount=Decimal("5000"),
            currency="INR",
        ),
        approval=Approval(),
    )


def _service(
    claims: list[ExpenseClaim] | None = None,
    *,
    submission_window_days: int = TravelValidationConfig.CLAIM_SUBMISSION_WINDOW_DAYS,
) -> TravelValidationService:
    """Build an isolated TravelValidationService backed by a fake repository."""
    repo = FakeClaimRepository(claims=claims)
    return TravelValidationService(
        claim_repository=repo,
        submission_window_days=submission_window_days,
    )


def _items_within_trip() -> list[ExpenseItem]:
    """One expense item on the first day of the reference trip."""
    return [_make_expense_item(_TRIP_START)]


###############################################################################
# Validation 1 — Future Trip
###############################################################################


class TestFutureTripValidation:
    """current_date < trip_start_date → FUTURE_TRIP"""

    def test_future_trip_raises(self) -> None:
        """Submitting before the trip starts must be rejected."""
        svc = _service()
        today = date(2026, 6, 20)  # before _TRIP_START (2026-07-01)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=_items_within_trip(),
                today=today,
            )

        err = exc_info.value
        assert err.error_code == "FUTURE_TRIP"
        assert "before travel begins" in err.message.lower() or "before travel" in err.message

    def test_trip_starting_today_passes(self) -> None:
        """
        A trip starting exactly today is NOT future travel.

        The employee may be on Day 1 of the trip and wants to pre-register;
        but per our rules, today == trip_start_date means ongoing (see V2),
        not future.  However, for the *future* check specifically, the
        boundary condition is current_date < trip_start_date, so today ==
        trip_start_date must NOT raise FUTURE_TRIP.

        Note: it will raise ONGOING_TRIP unless today == trip_end_date too.
        We only assert that FUTURE_TRIP is not the error.
        """
        svc = _service()
        today = _TRIP_START  # exactly start date

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=_items_within_trip(),
                today=today,
            )

        # FUTURE_TRIP must not fire; ONGOING_TRIP is expected instead
        assert exc_info.value.error_code != "FUTURE_TRIP"


###############################################################################
# Validation 2 — Ongoing Trip
###############################################################################


class TestOngoingTripValidation:
    """current_date < trip_end_date → ONGOING_TRIP"""

    def test_ongoing_trip_raises(self) -> None:
        """Submitting mid-trip must be rejected."""
        svc = _service()
        today = date(2026, 7, 4)  # between start (7-1) and end (7-7)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=_items_within_trip(),
                today=today,
            )

        err = exc_info.value
        assert err.error_code == "ONGOING_TRIP"
        assert "still in progress" in err.message.lower()

    def test_day_after_trip_end_passes_ongoing_check(self) -> None:
        """
        today > trip_end_date must not raise ONGOING_TRIP.

        (It may raise SUBMISSION_WINDOW_EXPIRED if the deadline is past,
        but we verify ONGOING_TRIP is not the error for this boundary.)
        """
        svc = _service()
        today = _TRIP_END + __import__("datetime").timedelta(days=1)

        try:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=_items_within_trip(),
                today=today,
            )
        except TravelValidationException as exc:
            assert exc.error_code != "ONGOING_TRIP"


###############################################################################
# Validation 3 — Submission Window
###############################################################################


class TestSubmissionWindowValidation:
    """Claims must be submitted within submission_window_days after trip end."""

    def test_within_window_passes(self) -> None:
        """Submitting on the last allowed day must succeed."""
        svc = _service()
        # trip ends 2026-07-07; window = 7; deadline = 2026-07-14
        today = date(2026, 7, 14)  # exactly on the deadline

        # No exception expected (all checks pass with empty repository)
        svc.validate_before_submission(
            employee_id=_EMPLOYEE_ID,
            trip_start_date=_TRIP_START,
            trip_end_date=_TRIP_END,
            expense_items=_items_within_trip(),
            today=today,
        )

    def test_expired_window_raises(self) -> None:
        """Submitting one day after the deadline must be rejected."""
        svc = _service()
        today = date(2026, 7, 15)  # one day past deadline (2026-07-14)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=_items_within_trip(),
                today=today,
            )

        err = exc_info.value
        assert err.error_code == "SUBMISSION_WINDOW_EXPIRED"
        assert str(TravelValidationConfig.CLAIM_SUBMISSION_WINDOW_DAYS) in err.message
        assert "2026-07-07" in err.message  # trip end date
        assert "2026-07-14" in err.message  # deadline
        assert "2026-07-15" in err.message  # current date

    def test_configurable_window(self) -> None:
        """A custom submission_window_days value is respected."""
        svc = _service(submission_window_days=3)
        # trip ends 2026-07-07; window = 3; deadline = 2026-07-10
        # submitting on 2026-07-11 should fail
        today = date(2026, 7, 11)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=_items_within_trip(),
                today=today,
            )

        assert exc_info.value.error_code == "SUBMISSION_WINDOW_EXPIRED"
        assert exc_info.value.metadata["submission_window_days"] == 3

    def test_default_window_is_seven_days(self) -> None:
        """Confirm the config constant equals 7 (company policy)."""
        assert TravelValidationConfig.CLAIM_SUBMISSION_WINDOW_DAYS == 7


###############################################################################
# Validation 4 — Existing Draft
###############################################################################


class TestExistingDraftValidation:
    """A DRAFT claim for the exact same trip period must be resumed."""

    def test_existing_draft_raises(self) -> None:
        """If a DRAFT exists for the same trip, EXISTING_DRAFT is raised."""
        draft = _make_claim(
            trip_start=_TRIP_START,
            trip_end=_TRIP_END,
            status=ClaimStatus.DRAFT,
            claim_id="CLM000000000001",
        )
        svc = _service(claims=[draft])
        today = date(2026, 7, 14)  # within submission window

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=_items_within_trip(),
                today=today,
            )

        err = exc_info.value
        assert err.error_code == "EXISTING_DRAFT"
        assert err.recoverable is True
        assert err.metadata["existing_claim_id"] == "CLM000000000001"

    def test_submitted_claim_does_not_trigger_draft_check(self) -> None:
        """
        A SUBMITTED claim for the same trip should trigger OVERLAPPING_TRIP,
        not EXISTING_DRAFT.
        """
        submitted = _make_claim(
            trip_start=_TRIP_START,
            trip_end=_TRIP_END,
            status=ClaimStatus.SUBMITTED,
            claim_id="CLM000000000002",
        )
        svc = _service(claims=[submitted])
        today = date(2026, 7, 14)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=_items_within_trip(),
                today=today,
            )

        assert exc_info.value.error_code == "OVERLAPPING_TRIP"


###############################################################################
# Validation 5 — Overlapping Trip
###############################################################################


class TestOverlappingTripValidation:
    """Dates must not intersect an existing active claim."""

    def _within_window(self) -> date:
        """A 'today' that passes all earlier checks (end + 3 days)."""
        return date(2026, 7, 10)

    def test_fully_contained_overlap_raises(self) -> None:
        """New trip fully inside existing trip → OVERLAPPING_TRIP."""
        existing = _make_claim(
            trip_start=date(2026, 7, 1),
            trip_end=date(2026, 7, 7),
            status=ClaimStatus.SUBMITTED,
        )
        svc = _service(claims=[existing])

        new_start = date(2026, 7, 4)
        new_end = date(2026, 7, 6)
        # today must be:
        #   > new_end  (clears ongoing-trip check)
        #   <= new_end + 7 days = 2026-07-13  (within submission window)
        today = date(2026, 7, 13)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=new_start,
                trip_end_date=new_end,
                expense_items=[_make_expense_item(new_start)],
                today=today,
            )

        assert exc_info.value.error_code == "OVERLAPPING_TRIP"

    def test_partial_overlap_raises(self) -> None:
        """New trip partially overlaps existing trip → OVERLAPPING_TRIP."""
        existing = _make_claim(
            trip_start=date(2026, 7, 1),
            trip_end=date(2026, 7, 7),
            status=ClaimStatus.APPROVED,
        )
        svc = _service(claims=[existing])

        new_start = date(2026, 7, 5)
        new_end = date(2026, 7, 10)
        today = date(2026, 7, 17)  # within 7-day window of new_end

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=new_start,
                trip_end_date=new_end,
                expense_items=[_make_expense_item(new_start)],
                today=today,
            )

        assert exc_info.value.error_code == "OVERLAPPING_TRIP"

    def test_adjacent_trips_do_not_overlap(self) -> None:
        """
        Trips that are adjacent (new starts the day after existing ends)
        must NOT trigger overlap detection.
        """
        existing = _make_claim(
            trip_start=date(2026, 7, 1),
            trip_end=date(2026, 7, 7),
            status=ClaimStatus.SUBMITTED,
        )
        svc = _service(claims=[existing])

        new_start = date(2026, 7, 8)  # day after existing ends
        new_end = date(2026, 7, 12)
        today = date(2026, 7, 19)  # within 7-day window of new_end

        # Should pass without raising
        svc.validate_before_submission(
            employee_id=_EMPLOYEE_ID,
            trip_start_date=new_start,
            trip_end_date=new_end,
            expense_items=[_make_expense_item(new_start)],
            today=today,
        )

    def test_rejected_claim_is_excluded_from_overlap_check(self) -> None:
        """A REJECTED claim must not block a new claim for the same period."""
        rejected = _make_claim(
            trip_start=_TRIP_START,
            trip_end=_TRIP_END,
            status=ClaimStatus.REJECTED,
        )
        svc = _service(claims=[rejected])
        today = date(2026, 7, 14)

        # Should pass — REJECTED is excluded from overlap detection
        svc.validate_before_submission(
            employee_id=_EMPLOYEE_ID,
            trip_start_date=_TRIP_START,
            trip_end_date=_TRIP_END,
            expense_items=_items_within_trip(),
            today=today,
        )

    def test_closed_claim_is_excluded_from_overlap_check(self) -> None:
        """A CLOSED claim must not block a new claim for the same period."""
        closed = _make_claim(
            trip_start=_TRIP_START,
            trip_end=_TRIP_END,
            status=ClaimStatus.CLOSED,
        )
        svc = _service(claims=[closed])
        today = date(2026, 7, 14)

        svc.validate_before_submission(
            employee_id=_EMPLOYEE_ID,
            trip_start_date=_TRIP_START,
            trip_end_date=_TRIP_END,
            expense_items=_items_within_trip(),
            today=today,
        )


###############################################################################
# Validation 6 — Expense Date Bounds
###############################################################################


class TestExpenseDateValidation:
    """Every expense item must fall within the declared trip period."""

    def test_expense_date_inside_trip_passes(self) -> None:
        """An expense on the last day of the trip is valid."""
        svc = _service()
        today = date(2026, 7, 14)  # within submission window

        svc.validate_before_submission(
            employee_id=_EMPLOYEE_ID,
            trip_start_date=_TRIP_START,
            trip_end_date=_TRIP_END,
            expense_items=[
                _make_expense_item(_TRIP_START),
                _make_expense_item(_TRIP_END),
                _make_expense_item(date(2026, 7, 4)),  # mid-trip
            ],
            today=today,
        )

    def test_expense_date_before_trip_raises(self) -> None:
        """An expense one day before trip start must be rejected."""
        svc = _service()
        today = date(2026, 7, 14)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=[_make_expense_item(date(2026, 6, 30))],  # before start
                today=today,
            )

        err = exc_info.value
        assert err.error_code == "EXPENSE_DATE_OUT_OF_RANGE"
        assert "2026-06-30" in err.message

    def test_expense_date_after_trip_raises(self) -> None:
        """An expense after trip end must be rejected."""
        svc = _service()
        today = date(2026, 7, 14)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=[_make_expense_item(date(2026, 7, 10))],  # after end
                today=today,
            )

        err = exc_info.value
        assert err.error_code == "EXPENSE_DATE_OUT_OF_RANGE"
        assert "2026-07-10" in err.message

    def test_only_first_invalid_expense_is_reported(self) -> None:
        """
        Fail-fast: only the first out-of-range expense is reported.
        Subsequent items are not checked once a failure occurs.
        """
        svc = _service()
        today = date(2026, 7, 14)

        out_of_range = _make_expense_item(date(2026, 7, 10), category_code="AIRFARE")
        also_bad = _make_expense_item(date(2026, 7, 11), category_code="HOTEL")

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=_TRIP_START,
                trip_end_date=_TRIP_END,
                expense_items=[out_of_range, also_bad],
                today=today,
            )

        # The first bad item's category must appear in the error
        assert exc_info.value.metadata["category_code"] == "AIRFARE"


###############################################################################
# Validation order — fail-fast guarantee
###############################################################################


class TestValidationOrder:
    """Validates that checks execute in the mandated order and stop early."""

    def test_future_trip_takes_priority_over_window(self) -> None:
        """
        If the trip is in the future AND the window would have expired,
        FUTURE_TRIP must fire first.
        """
        svc = _service()
        # A very old trip that is also in the future relative to today
        # (impossible in practice, but tests ordering isolation)
        trip_start = date(2026, 8, 1)
        trip_end = date(2026, 8, 5)
        today = date(2026, 7, 15)  # before start → future trip

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=trip_start,
                trip_end_date=trip_end,
                expense_items=[_make_expense_item(trip_start)],
                today=today,
            )

        assert exc_info.value.error_code == "FUTURE_TRIP"

    def test_ongoing_trip_takes_priority_over_window(self) -> None:
        """
        If the trip is ongoing the ONGOING_TRIP error fires before
        SUBMISSION_WINDOW_EXPIRED is evaluated.
        """
        svc = _service()
        # trip end is in the future relative to today → ongoing
        trip_start = date(2026, 7, 1)
        trip_end = date(2026, 7, 20)
        today = date(2026, 7, 10)

        with pytest.raises(TravelValidationException) as exc_info:
            svc.validate_before_submission(
                employee_id=_EMPLOYEE_ID,
                trip_start_date=trip_start,
                trip_end_date=trip_end,
                expense_items=[_make_expense_item(trip_start)],
                today=today,
            )

        assert exc_info.value.error_code == "ONGOING_TRIP"

    def test_all_checks_pass_clean_submission(self) -> None:
        """
        A genuinely valid submission with no existing claims and all
        expense items inside the trip window must succeed without error.
        """
        svc = _service()  # empty repository
        today = date(2026, 7, 12)  # within 7-day window of 2026-07-07

        svc.validate_before_submission(
            employee_id=_EMPLOYEE_ID,
            trip_start_date=_TRIP_START,
            trip_end_date=_TRIP_END,
            expense_items=[
                _make_expense_item(_TRIP_START),
                _make_expense_item(date(2026, 7, 4)),
                _make_expense_item(_TRIP_END),
            ],
            today=today,
        )
