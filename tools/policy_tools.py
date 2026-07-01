# """
# Policy Tools for AI Agents.

# This module provides native Strands tools that delegate policy and category operations to the
# ExpensePolicyService and ExpenseCategoryService. These tools are designed for use by AI agents and
# follow the Strands Agents SDK pattern.

# Tools are thin delegation layers that:
# - Call exactly one service method
# - Do not contain business logic
# - Do not implement policy calculations
# - Do not access repositories directly
# - Use existing domain models and exception handling
# - Follow project logging and typing conventions
# """

# from __future__ import annotations

# from strands import tool

# from services.expense_policy_service import ExpensePolicyService
# from services.expense_category_service import ExpenseCategoryService
# from models.expense_policy import ExpensePolicy
# from models.expense_category import ExpenseCategory
# from common.identifiers import CategoryId

# # Shared service instances for all tools in this module
# policy_service = ExpensePolicyService()
# category_service = ExpenseCategoryService()


# @tool
# def get_policy(
#     *,
#     category_id: CategoryId,
#     employee_grade: str,
# ) -> ExpensePolicy:
#     """
#     Retrieve the applicable expense policy for a category and employee grade.

#     This tool delegates to ExpensePolicyService.get_policy() to fetch
#     the specific policy that applies to an expense category and employee grade.

#     Args:
#         category_id: CategoryId of the expense category
#         employee_grade: Grade of the employee (determines policy limits)

#     Returns:
#         ExpensePolicy domain model with complete policy details including
#         daily limits, monthly limits, receipt requirements, and approval rules

#     Note:
#         This is a thin delegation layer. All policy lookup logic and
#         error handling is managed by the ExpensePolicyService. No policy
#         calculations or business rules are implemented in this tool.
#     """
#     return policy_service.get_policy(
#         category_id=category_id,
#         employee_grade=employee_grade,
#     )


# @tool
# def get_expense_category(
#     category_id: CategoryId,
# ) -> ExpenseCategory:
#     """
#     Retrieve details about an expense category.

#     This tool delegates to ExpenseCategoryService.get_category() to fetch
#     complete information about an expense category including its
#     requirements and configuration.

#     Args:
#         category_id: CategoryId of the expense category to retrieve

#     Returns:
#         ExpenseCategory domain model with category details including
#         name, description, receipt requirements, and approval rules

#     Note:
#         This is a thin delegation layer. All category retrieval logic and
#         error handling is managed by the ExpenseCategoryService. No category
#         validation or business rules are implemented in this tool.
#     """
#     return category_service.get_category(category_id)

from __future__ import annotations

from strands import tool

from models.expense_category import ExpenseCategory
from models.expense_policy import ExpensePolicy
from services.expense_category_service import ExpenseCategoryService
from services.expense_policy_service import ExpensePolicyService

category_service = ExpenseCategoryService()
policy_service = ExpensePolicyService()


@tool
def get_expense_category(
    category_code: str,
) -> ExpenseCategory:
    """
    Retrieve an expense category by code.
    """
    return category_service.get_category_by_code(category_code)


@tool
def get_policy(
    category_id: str,
    employee_grade: str,
) -> ExpensePolicy:
    """
    Retrieve the applicable expense policy.
    """
    return policy_service.get_policy(
        category_id=category_id,
        employee_grade=employee_grade,
    )
