"""
Expense Allowance Service.

Single source of truth for all monthly expense allowance calculations.

Responsibilities
----------------
- Calculate monthly allowance consumption per employee per category.
- Calculate remaining allowance per employee per category.
- Validate a claim's expense items against monthly allowance limits.
- Serve employee allowance queries (remaining, summary, category breakdown).

Architecture
------------
This service is the ONLY component that performs allowance calculations.
No agent, tool, or other service should duplicate these calculations.

    ExpenseAllowanceService
        │
        ├── ExpenseClaimRepository.get_monthly_category_consumption()
        │       Source of truth: APPROVED claims only
        │
        └── ExpensePolicyService.get_monthly_limit()
                Source of truth: policy monthly limits

Monthly Reset
-------------
No scheduler or cron is required.  Whenever a consumption query is made, it
filters claims to the current calendar month window (first_day … last_day).
At month rollover, the window shifts automatically and consumption starts at
zero because no APPROVED claims yet exist in the new month.

Source of Truth
---------------
Only APPROVED claims contribute toward monthly consumption.
DRAFT, SUBMITTED, UNDER_VALIDATION, VALIDATED, UNDER_REVIEW, REJECTED,
REIMBURSED, and CLOSED claims are never consumed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from models.allowance_validation_result import AllowanceValidationResult
from repositories.expense_claim_repository import ExpenseClaimRepository
from services.base import BaseService
from services.expense_category_service import ExpenseCategoryService
from services.expense_policy_service import ExpensePolicyService


def _current_year_month() -> tuple[int, int]:
    """Return (year, month) for the current UTC calendar month."""
    now = datetime.now(UTC)
    return now.year, now.month


class ExpenseAllowanceService(BaseService):
    """
    Enterprise Expense Allowance Service.

    Calculates, validates, and reports monthly expense allowances for
    employees.  This is the single reusable business component responsible
    for all allowance-related logic.

    Methods
    -------
    calculate_monthly_consumption(employee_id, category_code)
        Return total approved amount consumed this month for a category.

    get_remaining_allowance(employee_id, category_code, employee_grade)
        Return remaining allowance for a category this month.

    get_category_allowance(employee_id, category_code, employee_grade,
                           requested_amount)
        Return a structured AllowanceValidationResult for a category.

    get_employee_allowance_summary(employee_id, employee_grade, categories)
        Return remaining allowance for every requested category.

    validate_claim_allowance(employee_id, employee_grade, expense_items)
        Validate all expense items in a claim against monthly limits.
        Returns a list of AllowanceValidationResult — one per category.
    """

    def __init__(self) -> None:
        super().__init__()
        self.claim_repository = ExpenseClaimRepository()
        self.policy_service = ExpensePolicyService()
        self.category_service = ExpenseCategoryService()

    ###########################################################################
    # Public API — Consumption
    ###########################################################################

    def calculate_monthly_consumption(
        self,
        employee_id: str,
        category_code: str,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> Decimal:
        """
        Return the total approved amount consumed this month for a category.

        Queries only APPROVED claims for the given employee and category
        within the specified (or current) calendar month.

        Parameters
        ----------
        employee_id:
            Employee identifier.
        category_code:
            Expense category code (e.g. HOTEL, MEALS).
        year:
            Calendar year override (defaults to current UTC year).
        month:
            Calendar month override (defaults to current UTC month).

        Returns
        -------
        Decimal
            Total approved amount; Decimal("0.00") when no approved claims exist.
        """
        self.logger.info(
            "Monthly Consumption Retrieved — employee=%s, category=%s",
            employee_id,
            category_code,
        )

        y, m = year or _current_year_month()[0], month or _current_year_month()[1]
        if year and month:
            y, m = year, month
        elif year:
            y = year
            _, m = _current_year_month()
        elif month:
            _, m = _current_year_month()
            y, _ = _current_year_month()
        else:
            y, m = _current_year_month()

        consumption = self.claim_repository.get_monthly_category_consumption(
            employee_id=employee_id,
            category_code=category_code.strip().upper(),
            year=y,
            month=m,
        )

        self.logger.info(
            "Monthly Consumption: employee=%s, category=%s, month=%d/%d, consumed=%s",
            employee_id,
            category_code,
            m,
            y,
            consumption,
        )

        return consumption

    ###########################################################################
    # Public API — Remaining Allowance
    ###########################################################################

    def get_remaining_allowance(
        self,
        employee_id: str,
        category_code: str,
        employee_grade: str,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> Decimal:
        """
        Return the remaining monthly allowance for a category.

        Computes: remaining = monthly_limit - already_consumed.
        Remaining is never negative.

        Parameters
        ----------
        employee_id:
            Employee identifier.
        category_code:
            Expense category code.
        employee_grade:
            Employee grade used to fetch the applicable policy.
        year:
            Calendar year override.
        month:
            Calendar month override.

        Returns
        -------
        Decimal
            Remaining allowance; clamped to zero from below.
        """
        self.logger.info(
            "Hotel Remaining Calculated — employee=%s, category=%s, grade=%s",
            employee_id,
            category_code,
            employee_grade,
        )

        monthly_limit = self.policy_service.get_monthly_limit(
            category_identifier=category_code,
            employee_grade=employee_grade,
        )

        y, m = _current_year_month()
        if year:
            y = year
        if month:
            m = month

        already_consumed = self.claim_repository.get_monthly_category_consumption(
            employee_id=employee_id,
            category_code=category_code.strip().upper(),
            year=y,
            month=m,
        )

        remaining = max(Decimal("0.00"), monthly_limit - already_consumed)

        self.logger.info(
            "Remaining Allowance: employee=%s, category=%s, limit=%s, consumed=%s, remaining=%s",
            employee_id,
            category_code,
            monthly_limit,
            already_consumed,
            remaining,
        )

        return remaining

    ###########################################################################
    # Public API — Category Allowance (Structured Result)
    ###########################################################################

    def get_category_allowance(
        self,
        employee_id: str,
        category_code: str,
        employee_grade: str,
        requested_amount: Decimal = Decimal("0.00"),
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> AllowanceValidationResult:
        """
        Return a structured AllowanceValidationResult for a single category.

        This method is the core building block used by both
        validate_claim_allowance() and the allowance query tools.

        Parameters
        ----------
        employee_id:
            Employee identifier.
        category_code:
            Expense category code.
        employee_grade:
            Employee grade used to resolve the applicable policy.
        requested_amount:
            Amount the employee wishes to claim (default 0 for query-only use).
        year:
            Calendar year override.
        month:
            Calendar month override.

        Returns
        -------
        AllowanceValidationResult
            Structured result with limit, consumed, remaining, and verdict.
        """
        self.logger.info(
            "Allowance Summary Retrieved — employee=%s, category=%s",
            employee_id,
            category_code,
        )

        # Resolve category to get the canonical name
        category = self.category_service.resolve_category(category_code)

        monthly_limit = self.policy_service.get_monthly_limit(
            category_identifier=category.category_code,
            employee_grade=employee_grade,
        )

        y, m = _current_year_month()
        if year:
            y = year
        if month:
            m = month

        already_consumed = self.claim_repository.get_monthly_category_consumption(
            employee_id=employee_id,
            category_code=category.category_code.strip().upper(),
            year=y,
            month=m,
        )

        result = AllowanceValidationResult.build(
            category_code=category.category_code,
            category_name=category.category_name,
            monthly_limit=monthly_limit,
            already_consumed=already_consumed,
            requested_amount=requested_amount,
            currency="INR",
        )

        self.logger.info(
            "Category Allowance: employee=%s, category=%s, limit=%s, consumed=%s, remaining=%s, requested=%s, exceeded=%s",
            employee_id,
            category_code,
            monthly_limit,
            already_consumed,
            result.remaining,
            requested_amount,
            result.exceeded,
        )

        return result

    ###########################################################################
    # Public API — Employee Allowance Summary
    ###########################################################################

    def get_employee_allowance_summary(
        self,
        employee_id: str,
        employee_grade: str,
        categories: list[str] | None = None,
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> dict[str, Any]:
        """
        Return a comprehensive monthly allowance summary for an employee.

        When ``categories`` is None or empty, calculates the summary for
        all categories that have active policies for this employee grade.

        Parameters
        ----------
        employee_id:
            Employee identifier.
        employee_grade:
            Employee grade used to resolve applicable policies.
        categories:
            Optional list of category codes to include.  If omitted all
            categories with active policies for this grade are included.
        year:
            Calendar year override.
        month:
            Calendar month override.

        Returns
        -------
        dict with keys:
            employee_id, employee_grade, year, month,
            categories (list of AllowanceValidationResult.summary_dict()),
            total_monthly_limit, total_consumed, total_remaining
        """
        self.logger.info(
            "Expense Allowance Validation Started — employee=%s, grade=%s",
            employee_id,
            employee_grade,
        )

        y, m = _current_year_month()
        if year:
            y = year
        if month:
            m = month

        # Resolve which categories to report
        if not categories:
            active_policies = self.policy_service.list_active_policies()
            categories = list(
                {p.category_id for p in active_policies if p.employee_grade == employee_grade}
            )

        category_results: list[dict] = []
        total_limit = Decimal("0.00")
        total_consumed = Decimal("0.00")
        total_remaining = Decimal("0.00")

        for cat_identifier in categories:
            try:
                result = self.get_category_allowance(
                    employee_id=employee_id,
                    category_code=cat_identifier,
                    employee_grade=employee_grade,
                    requested_amount=Decimal("0.00"),
                    year=y,
                    month=m,
                )
                category_results.append(result.summary_dict())
                total_limit += result.monthly_limit
                total_consumed += result.already_consumed
                total_remaining += result.remaining
            except Exception as exc:
                self.logger.warning(
                    "Could not compute allowance for category '%s': %s",
                    cat_identifier,
                    exc,
                )

        self.logger.info(
            "Expense Allowance Service Completed — employee=%s, categories=%d",
            employee_id,
            len(category_results),
        )

        return {
            "employee_id": employee_id,
            "employee_grade": employee_grade,
            "year": y,
            "month": m,
            "categories": category_results,
            "total_monthly_limit": str(total_limit),
            "total_consumed": str(total_consumed),
            "total_remaining": str(total_remaining),
        }

    ###########################################################################
    # Public API — Claim Allowance Validation
    ###########################################################################

    def validate_claim_allowance(
        self,
        employee_id: str,
        employee_grade: str,
        expense_items: list[dict],
        *,
        year: int | None = None,
        month: int | None = None,
    ) -> list[AllowanceValidationResult]:
        """
        Validate all expense items in a claim against monthly allowance limits.

        Each category is validated independently.  A single failed category
        does not short-circuit remaining validations — all results are returned
        so the employee sees the complete picture.

        Parameters
        ----------
        employee_id:
            Employee submitting the claim.
        employee_grade:
            Grade used to resolve applicable policies.
        expense_items:
            List of dicts with at least ``category_code`` and
            ``requested_amount`` keys.
        year:
            Calendar year override (defaults to current UTC year).
        month:
            Calendar month override (defaults to current UTC month).

        Returns
        -------
        list[AllowanceValidationResult]
            One result per expense item.  Callers should check
            ``any(r.exceeded for r in results)`` to determine overall failure.
        """
        self.logger.info(
            "Expense Allowance Validation Started — employee=%s, grade=%s, items=%d",
            employee_id,
            employee_grade,
            len(expense_items),
        )

        y, m = _current_year_month()
        if year:
            y = year
        if month:
            m = month

        results: list[AllowanceValidationResult] = []

        for item in expense_items:
            category_code = str(item.get("category_code") or "").strip()
            if not category_code:
                continue

            requested_raw = item.get("requested_amount", Decimal("0.00"))
            requested_amount = (
                Decimal(str(requested_raw))
                if not isinstance(requested_raw, Decimal)
                else requested_raw
            )

            try:
                result = self.get_category_allowance(
                    employee_id=employee_id,
                    category_code=category_code,
                    employee_grade=employee_grade,
                    requested_amount=requested_amount,
                    year=y,
                    month=m,
                )
                results.append(result)

                if result.exceeded:
                    self.logger.warning(
                        "Allowance Validation Failed — employee=%s, category=%s, exceeded_by=%s",
                        employee_id,
                        category_code,
                        result.exceeded_by,
                    )
                else:
                    self.logger.info(
                        "Allowance Validation Passed — employee=%s, category=%s, remaining=%s",
                        employee_id,
                        category_code,
                        result.remaining,
                    )

            except Exception as exc:
                self.logger.error(
                    "Allowance validation error for category '%s': %s",
                    category_code,
                    exc,
                )
                raise

        overall_passed = all(not r.exceeded for r in results)
        if overall_passed:
            self.logger.info(
                "Expense Allowance Service Completed — All categories passed for employee=%s",
                employee_id,
            )
        else:
            self.logger.warning(
                "Expense Allowance Service Completed — Some categories exceeded for employee=%s",
                employee_id,
            )

        return results


__all__ = ["ExpenseAllowanceService"]
