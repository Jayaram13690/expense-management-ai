"""
Expense Allowance Tools for AI Agents.

These tools expose ExpenseAllowanceService to the Expense Agent.

Architecture
------------
    ExpenseAgent → @tool → ExpenseAllowanceService → ExpenseClaimRepository

Design Principles
-----------------
- Each tool delegates to exactly one service method.
- No business logic lives in these tools.
- Tools return structured results (AllowanceValidationResult) or plain dicts.
- Agents use these tools; they do not call the service directly.
"""

from __future__ import annotations

from decimal import Decimal

from strands import tool

from models.allowance_validation_result import AllowanceValidationResult
from services.expense_allowance_service import ExpenseAllowanceService

# One shared service instance for all tools in this module
_allowance_service = ExpenseAllowanceService()


def _resolve_grade(employee_id: str, employee_grade: str | None) -> str:
    """
    Return employee_grade as-is if provided, otherwise look it up from
    EmployeeService using employee_id.

    Raises ValueError if grade cannot be resolved.
    """
    if employee_grade:
        return employee_grade.strip()

    from services.employee_service import EmployeeService

    employee = EmployeeService().try_get_employee(employee_id)
    if employee is None:
        raise ValueError(
            f"Employee '{employee_id}' not found. Cannot resolve employee grade."
        )
    grade = getattr(employee, "grade", None) or getattr(employee, "employee_grade", None)
    if not grade:
        raise ValueError(
            f"Employee '{employee_id}' has no grade configured."
        )
    return str(grade)


@tool
def validate_allowance_tool(
    employee_id: str,
    expense_items: list[dict],
    employee_grade: str | None = None,
) -> dict:
    """
    Validate all expense items in a claim against monthly allowance limits.

    This tool should be called after Variance Calculation and before
    Claim Summary in the sequential workflow.

    Each expense category is validated independently.  The result lists
    every category and whether the monthly allowance would be exceeded.

    Args:
        employee_id:
            Employee identifier (e.g. EMP0007).
        expense_items:
            List of dicts.  Each dict must contain:
            - ``category_code`` (str): e.g. HOTEL, MEALS, TAXI
            - ``requested_amount`` (str or number): amount being claimed
        employee_grade:
            Optional. Employee grade (e.g. G5). If omitted, it is looked
            up automatically from the employee record.

    Returns:
        dict with keys:
            - ``passed`` (bool): True when ALL categories are within limits.
            - ``results`` (list): One summary dict per expense item.
            - ``exceeded_categories`` (list): Category codes that exceeded limits.
            - ``message`` (str): Human-readable overall verdict.
    """
    grade = _resolve_grade(employee_id, employee_grade)

    results: list[AllowanceValidationResult] = _allowance_service.validate_claim_allowance(
        employee_id=employee_id,
        employee_grade=grade,
        expense_items=expense_items,
    )

    passed = all(not r.exceeded for r in results)
    exceeded_categories = [r.category_code for r in results if r.exceeded]

    if passed:
        message = "All expense categories are within the monthly allowance limits."
    else:
        exceeded_details = "; ".join(
            f"{r.category_name}: exceeded by INR {r.exceeded_by:,}"
            for r in results
            if r.exceeded
        )
        message = (
            f"Monthly allowance exceeded for: {exceeded_details}. "
            "Please review and modify your expenses before submitting."
        )

    return {
        "passed": passed,
        "results": [r.summary_dict() for r in results],
        "exceeded_categories": exceeded_categories,
        "message": message,
    }


@tool
def get_remaining_allowance_tool(
    employee_id: str,
    category_code: str,
    employee_grade: str | None = None,
) -> dict:
    """
    Return the remaining monthly allowance for a specific expense category.

    Use this tool when the employee asks:
    - "How much hotel allowance do I have left this month?"
    - "How much meal allowance have I used?"
    - "How much taxi allowance do I have left?"
    - "How much hotel allowance left for EMP0002 this month?"

    Args:
        employee_id:
            Employee identifier (e.g. EMP0002).
        category_code:
            Expense category code (e.g. HOTEL, MEALS, TAXI, AIR).
        employee_grade:
            Optional. Employee grade (e.g. G9). If omitted, it is looked
            up automatically from the employee record.

    Returns:
        dict with keys:
            - ``category_code`` (str)
            - ``category_name`` (str)
            - ``monthly_limit`` (str): Policy monthly limit in INR.
            - ``already_consumed`` (str): Amount consumed from APPROVED claims.
            - ``remaining`` (str): Remaining allowance (never negative).
            - ``currency`` (str)
            - ``message`` (str): Human-readable allowance summary.
    """
    grade = _resolve_grade(employee_id, employee_grade)

    result = _allowance_service.get_category_allowance(
        employee_id=employee_id,
        category_code=category_code,
        employee_grade=grade,
        requested_amount=Decimal("0.00"),
    )

    message = (
        f"{result.category_name} Allowance Summary\n"
        f"Monthly Limit    : {result.currency} {result.monthly_limit:,}\n"
        f"Already Consumed : {result.currency} {result.already_consumed:,}\n"
        f"Remaining        : {result.currency} {result.remaining:,}\n\n"
        f"You can still claim up to {result.currency} {result.remaining:,} "
        f"for {result.category_name.lower()} expenses this month."
    )

    return {
        "category_code": result.category_code,
        "category_name": result.category_name,
        "monthly_limit": str(result.monthly_limit),
        "already_consumed": str(result.already_consumed),
        "remaining": str(result.remaining),
        "currency": result.currency,
        "message": message,
    }


@tool
def get_allowance_summary_tool(
    employee_id: str,
    categories: list[str] | None = None,
    employee_grade: str | None = None,
) -> dict:
    """
    Return a comprehensive monthly allowance summary for an employee.

    Use this tool when the employee asks:
    - "Show my monthly allowance."
    - "Show my monthly spending."
    - "Show my allowance by category."
    - "What are my remaining allowances?"
    - "Show allowance summary for EMP0002."

    Args:
        employee_id:
            Employee identifier.
        categories:
            Optional list of category codes to include.  If omitted, all
            categories with active policies for this grade are returned.
        employee_grade:
            Optional. Employee grade (e.g. G9). If omitted, it is looked
            up automatically from the employee record.

    Returns:
        dict with keys:
            - ``employee_id`` (str)
            - ``employee_grade`` (str)
            - ``year`` (int)
            - ``month`` (int)
            - ``categories`` (list): One summary dict per category.
            - ``total_monthly_limit`` (str)
            - ``total_consumed`` (str)
            - ``total_remaining`` (str)
    """
    grade = _resolve_grade(employee_id, employee_grade)

    return _allowance_service.get_employee_allowance_summary(
        employee_id=employee_id,
        employee_grade=grade,
        categories=categories,
    )


__all__ = [
    "validate_allowance_tool",
    "get_remaining_allowance_tool",
    "get_allowance_summary_tool",
]
