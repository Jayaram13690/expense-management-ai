"""
Policy Tools for AI Agents.

This module provides native Strands tools that delegate policy and category
operations to ExpensePolicyService and ExpenseCategoryService.

Tools are thin delegation layers that:

- Call exactly one service method.
- Do not contain business logic.
- Do not implement policy calculations.
- Do not access repositories directly.
- Use existing domain models and exception handling.
- Follow project logging and typing conventions.
"""

from __future__ import annotations

from strands import tool

from models.expense_category import ExpenseCategory
from models.expense_policy import ExpensePolicy
from services.expense_category_service import ExpenseCategoryService
from services.expense_policy_service import ExpensePolicyService

# Shared service instances for all tools in this module.
category_service = ExpenseCategoryService()
policy_service = ExpensePolicyService()


@tool
def get_expense_category(
    category_identifier: str,
) -> ExpenseCategory:
    """
    Resolve and retrieve an expense category.

    Accepts any supported category identifier:

    - ``category_id``   — e.g. ``CAT0001``
    - ``category_code`` — e.g. ``HOTEL``, ``TAXI``, ``AIR``, ``MEALS``
    - ``category_name`` — e.g. ``Hotel``, ``Taxi``, ``Meals``, ``Hotel Accommodation``

    This tool delegates to ExpenseCategoryService.resolve_category() which
    automatically applies the correct lookup strategy.  The LLM must never
    attempt to determine the identifier type itself.

    Args:
        category_identifier: Any category identifier supplied by the user.

    Returns:
        ExpenseCategory domain model with full category details including
        category_id, category_code, category_name, description, and
        receipt/approval requirements.

    Note:
        If no category matches the supplied identifier a ServiceException is
        raised with a clear user-readable message.  Do not attempt to call
        downstream policy tools when this tool reports a failure.
    """

    return category_service.resolve_category(category_identifier)


@tool
def get_policy_by_identifier(
    category_identifier: str,
    employee_grade: str,
) -> ExpensePolicy:
    """
    Retrieve the applicable expense policy using any category identifier.

    Supports category_id (CAT0001), category_code (HOTEL, TAXI), or
    category_name (Hotel Accommodation) with automatic resolution.

    Args:
        category_identifier: Category ID, code, or name.
        employee_grade: Grade of the employee (determines policy limits).

    Returns:
        ExpensePolicy domain model with complete policy details including
        daily limits, monthly limits, receipt requirements, and approval rules.

    Note:
        This is a thin delegation layer.  All category resolution and policy
        lookup logic is managed by the service layer.
    """

    return policy_service.get_policy_by_identifier(
        category_identifier=category_identifier,
        employee_grade=employee_grade,
    )


@tool
def check_employee_eligibility(
    category_identifier: str,
    employee_grade: str,
) -> bool:
    """
    Check if an employee grade is eligible for an expense category.

    Args:
        category_identifier: Category ID, code, or name.
        employee_grade: Grade of the employee.

    Returns:
        True if a policy exists for the category and grade, False otherwise.
    """

    return policy_service.check_employee_eligibility(
        category_identifier=category_identifier,
        employee_grade=employee_grade,
    )


@tool
def get_category_limits(
    category_identifier: str,
    employee_grade: str,
) -> dict:
    """
    Retrieve expense category limits for an employee grade.

    Args:
        category_identifier: Category ID, code, or name.
        employee_grade: Grade of the employee.

    Returns:
        Dictionary containing daily_limit, monthly_limit,
        receipt_required, and approval_required.
    """

    return policy_service.get_category_limits(
        category_identifier=category_identifier,
        employee_grade=employee_grade,
    )


@tool
def get_reimbursement_rules(
    category_identifier: str,
    employee_grade: str,
) -> dict:
    """
    Retrieve reimbursement rules for an expense category and employee grade.

    Args:
        category_identifier: Category ID, code, or name.
        employee_grade: Grade of the employee.

    Returns:
        Dictionary containing reimbursement_percentage, processing_time_days,
        currency, and special_conditions.
    """

    return policy_service.get_reimbursement_rules(
        category_identifier=category_identifier,
        employee_grade=employee_grade,
    )
