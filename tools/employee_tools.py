# """
# Employee Tools for AI Agents.

# This module provides native Strands tools that delegate employee-related operations to the
# EmployeeService and ExpenseClaimService. These tools are designed for use by AI agents and
# follow the Strands Agents SDK pattern.

# Tools are thin delegation layers that:
# - Call exactly one service method
# - Do not contain business logic
# - Do not access repositories directly
# - Use existing domain models and exception handling
# - Follow project logging and typing conventions
# """

# from __future__ import annotations

# from strands import tool

# from services.employee_service import EmployeeService
# from services.expense_claim_service import ExpenseClaimService
# from models.employee import Employee
# from models.expense_claim import ExpenseClaim
# from common.identifiers import EmployeeId

# # Shared service instances for all tools in this module
# employee_service = EmployeeService()
# expense_claim_service = ExpenseClaimService()


# @tool
# def get_employee_details(
#     employee_id: EmployeeId,
# ) -> Employee:
#     """
#     Retrieve detailed information about an employee.

#     This tool delegates to EmployeeService.get_employee() to fetch
#     complete employee details including personal information,
#     employment details, and organizational hierarchy.

#     Args:
#         employee_id: EmployeeId of the employee to retrieve

#     Returns:
#         Employee domain model with full employee details

#     Note:
#         This is a thin delegation layer. All retrieval logic and
#         error handling is managed by the EmployeeService.
#     """
#     return employee_service.get_employee(employee_id)


# @tool
# def list_employee_claims(
#     employee_id: EmployeeId,
# ) -> list[ExpenseClaim]:
#     """
#     Retrieve all expense claims submitted by an employee.

#     This tool delegates to ExpenseClaimService.list_employee_claims() to fetch
#     all claims associated with a specific employee, ordered by submission date.

#     Args:
#         employee_id: EmployeeId of the employee whose claims to retrieve

#     Returns:
#         List of ExpenseClaim aggregates submitted by the employee

#     Note:
#         This is a thin delegation layer. All query logic and
#         error handling is managed by the ExpenseClaimService.
#     """
#     return expense_claim_service.list_employee_claims(employee_id)


from __future__ import annotations

from strands import tool

from models.employee import Employee
from models.expense_claim import ExpenseClaim
from services.employee_service import EmployeeService
from services.expense_claim_service import ExpenseClaimService

employee_service = EmployeeService()
expense_claim_service = ExpenseClaimService()


@tool
def get_employee_details(
    employee_id: str,
) -> Employee:
    """
    Retrieve employee details.

    Args:
        employee_id:
            Employee identifier.

    Returns:
        Employee domain model.
    """
    return employee_service.get_employee(employee_id)


@tool
def list_employee_claims(
    employee_id: str,
) -> list[ExpenseClaim]:
    """
    Retrieve all expense claims submitted by an employee.

    Args:
        employee_id:
            Employee identifier.

    Returns:
        List of ExpenseClaim aggregates.
    """
    return expense_claim_service.list_employee_claims(employee_id)
