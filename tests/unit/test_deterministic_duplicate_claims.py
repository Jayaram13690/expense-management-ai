from __future__ import annotations

import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import pytest

from agents import __all__ as _unused  # noqa: F401
from common.identifiers import EmployeeId
from exceptions.repository import RepositoryException
from exceptions.service import ServiceException
from models.dto.expense_item import ExpenseItem
from models.dto.submit_claim import SubmitExpenseClaimRequest
from models.employee import Employee
from models.expense_category import ExpenseCategory
from models.expense_claim import ExpenseClaim
from models.expense_policy import ExpensePolicy
from services.expense_claim_service import ExpenseClaimService


class FakeExpenseClaimRepository:
    def __init__(self) -> None:
        self.by_id: dict[str, ExpenseClaim] = {}
        self.by_business_key: dict[str, ExpenseClaim] = {}
        self.lock = threading.Lock()
        self.barrier: threading.Barrier | None = None

    def list_employee_claims(self, employee_id: str) -> list[ExpenseClaim]:
        return [
            copy.deepcopy(claim)
            for claim in self.by_id.values()
            if claim.employee_id == employee_id
        ]

    def claim_exists(self, claim_id: str) -> bool:
        return claim_id in self.by_id

    def update(self, claim: ExpenseClaim) -> ExpenseClaim:
        self.by_id[claim.claim_id] = copy.deepcopy(claim)
        if claim.business_key:
            self.by_business_key[claim.business_key] = copy.deepcopy(claim)
        return claim

    def save(self, claim: ExpenseClaim) -> ExpenseClaim:
        if self.claim_exists(claim.claim_id):
            return self.update(claim)
        return self.create_with_business_key(claim)

    def create_with_business_key(self, claim: ExpenseClaim) -> ExpenseClaim:
        if self.barrier is not None:
            self.barrier.wait(timeout=5)

        business_key = claim.business_key or ExpenseClaim.business_key_from_claim(claim)
        with self.lock:
            if business_key in self.by_business_key:
                existing = self.by_business_key[business_key]
                raise RepositoryException(
                    message="Expense claim already exists for this employee and trip.",
                    error_code="CLAIM_ALREADY_EXISTS",
                    metadata={
                        "business_key": business_key,
                        "duplicate_claim": existing.model_dump(mode="python"),
                    },
                )
            stored = copy.deepcopy(claim)
            stored.business_key = business_key
            self.by_id[stored.claim_id] = stored
            self.by_business_key[business_key] = stored
            return stored

    def get_claim_by_business_key(self, business_key: str) -> ExpenseClaim | None:
        claim = self.by_business_key.get(business_key)
        return copy.deepcopy(claim) if claim is not None else None


def _build_service(repository: FakeExpenseClaimRepository) -> ExpenseClaimService:
    service = ExpenseClaimService()
    service.claim_repository = repository
    service.employee_service.get_employee = lambda employee_id: _employee(employee_id)
    service.category_service.get_category_by_code = lambda code: _category(code)
    service.policy_service.get_policy = lambda category_id, employee_grade: _policy(
        category_id, employee_grade
    )
    # Bypass travel validation in these tests: they test duplicate-detection /
    # business-key logic only.  Trip dates are fixed past dates that would
    # otherwise trigger SUBMISSION_WINDOW_EXPIRED.  Travel validation has its
    # own dedicated test suite (test_travel_validation_service.py).
    service.travel_validation_service.validate_before_submission = lambda **kwargs: None
    return service


def _employee(employee_id: EmployeeId) -> Employee:
    return Employee(
        employee_id=employee_id,
        first_name="Asha",
        last_name="Rao",
        email="asha.rao@example.com",
        department="Engineering",
        designation="Engineer",
        grade="G5",
        manager_id="MGR001",
        cost_center="CC100",
        location="Bangalore",
    )


def _category(code: str) -> ExpenseCategory:
    normalized = code.strip().upper()
    category_id = sum((index + 1) * ord(char) for index, char in enumerate(normalized)) % 10_000_000
    return ExpenseCategory(
        category_id=f"CAT{category_id:07d}",
        category_code=normalized,
        category_name=normalized.title(),
        description=f"{normalized} expenses",
        reimbursement_required=True,
        receipt_required=False,
        approval_required=False,
    )


def _policy(category_id: str, employee_grade: str) -> ExpensePolicy:
    policy_id = sum((index + 1) * ord(char) for index, char in enumerate(category_id)) % 10_000_000
    return ExpensePolicy(
        policy_id=f"POL{policy_id:07d}",
        employee_grade=employee_grade,
        category_id=category_id,
        daily_limit=Decimal("10000"),
        monthly_limit=Decimal("50000"),
        receipt_required=False,
        approval_required=False,
        currency="INR",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )


def _request(
    *,
    trip_name: str = "Client Meeting Travel Expense",
    destination: str = "Bangalore",
    trip_start_date: date = date(2026, 7, 1),
    trip_end_date: date = date(2026, 7, 3),
    categories: list[str] | None = None,
) -> SubmitExpenseClaimRequest:
    category_list = categories or ["AIR", "HOTEL", "MEALS"]
    return SubmitExpenseClaimRequest(
        employee_id="EMP0003",
        trip_name=trip_name,
        business_purpose="Attend customer meetings for project planning.",
        destination=destination,
        trip_start_date=trip_start_date,
        trip_end_date=trip_end_date,
        comments="Unit test",
        expense_items=[
            ExpenseItem(
                category_code=category,
                description=f"{category} expense",
                expense_date=trip_start_date,
                requested_amount=Decimal("1000"),
                currency="INR",
                receipt_available=True,
            )
            for category in category_list
        ],
    )


def _submit(service: ExpenseClaimService, request: SubmitExpenseClaimRequest) -> ExpenseClaim:
    return service.submit_claim(request)


def test_business_key_normalization_handles_whitespace_and_case() -> None:
    base = ExpenseClaim.build_business_key(
        employee_id="EMP0003",
        trip_name="Client Meeting Travel Expense",
        destination="Bangalore",
        trip_start_date=date(2026, 7, 1),
        trip_end_date=date(2026, 7, 3),
        expense_categories=["AIR", "HOTEL", "MEALS", "HOTEL"],
    )
    variant = ExpenseClaim.build_business_key(
        employee_id=" emp0003 ",
        trip_name="  client meeting travel expense  ",
        destination="  bangalore  ",
        trip_start_date=date(2026, 7, 1),
        trip_end_date=date(2026, 7, 3),
        expense_categories=["meals", "hotel", "air", "air"],
    )

    assert base == variant
    assert (
        base
        == "EMP0003|client meeting travel expense|bangalore|2026-07-01|2026-07-03|AIR,HOTEL,MEALS"
    )


def test_exact_duplicate_claim_is_rejected_and_returns_existing_claim_metadata() -> None:
    repository = FakeExpenseClaimRepository()
    service = _build_service(repository)
    first = _submit(service, _request())

    with pytest.raises(ServiceException) as exc_info:
        _submit(service, _request())

    assert first.business_key is not None
    assert exc_info.value.error_code == "CLAIM_ALREADY_EXISTS"
    assert "already exists" in exc_info.value.message.lower()


@pytest.mark.parametrize(
    ("field_name", "request_a", "request_b"),
    [
        (
            "destination",
            _request(),
            _request(destination="Mumbai"),
        ),
        (
            "trip dates",
            _request(),
            _request(trip_start_date=date(2026, 7, 2), trip_end_date=date(2026, 7, 4)),
        ),
        (
            "category set",
            _request(),
            _request(categories=["AIR", "HOTEL"]),
        ),
    ],
)
def test_non_duplicate_variants_are_allowed(
    field_name: str,
    request_a: SubmitExpenseClaimRequest,
    request_b: SubmitExpenseClaimRequest,
) -> None:
    repository = FakeExpenseClaimRepository()
    service = _build_service(repository)

    first = _submit(service, request_a)
    second = _submit(service, request_b)

    assert first.claim_id != second.claim_id
    assert len(repository.by_id) == 2
    assert len(repository.by_business_key) == 2, field_name


def test_concurrent_submissions_only_persist_once() -> None:
    repository = FakeExpenseClaimRepository()
    repository.barrier = threading.Barrier(2)
    service = _build_service(repository)
    request = _request()

    def run_submission() -> ExpenseClaim | ServiceException:
        try:
            return _submit(service, request)
        except ServiceException as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: run_submission(), range(2)))

    successes = [result for result in results if isinstance(result, ExpenseClaim)]
    failures = [result for result in results if isinstance(result, ServiceException)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].error_code == "CLAIM_ALREADY_EXISTS"
    assert failures[0].metadata["duplicate_claim"]["claim_id"] == successes[0].claim_id
    assert len(repository.by_id) == 1
    assert len(repository.by_business_key) == 1
