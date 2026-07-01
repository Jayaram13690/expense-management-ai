# """
# Approval Tools for AI Agents.

# This module provides native Strands tools that delegate claim approval operations to the
# ExpenseClaimService. These tools are designed for use by AI agents and follow the
# Strands Agents SDK pattern.

# Tools are thin delegation layers that:
# - Call exactly one service method
# - Do not contain business logic
# - Do not access repositories directly
# - Use existing domain models and exception handling
# - Follow project logging and typing conventions
# """

# from __future__ import annotations

# from strands import tool

# from services.expense_claim_service import ExpenseClaimService
# from models.expense_claim import ExpenseClaim
# from common.identifiers import ClaimId, EmployeeId

# # Shared service instance for all tools in this module
# expense_claim_service = ExpenseClaimService()


# @tool
# def approve_claim(
#     claim_id: ClaimId,
#     approver_id: EmployeeId,
#     approver_name: str,
#     ) -> ExpenseClaim:
#     """
#     Approve an expense claim.

#     This tool delegates to ExpenseClaimService.approve_claim() to transition
#     a claim to APPROVED status and record the approval decision.

#     Args:
#         claim_id: ClaimId of the claim to approve
#         approver_id: EmployeeId of the approving manager
#         approver_name: Full name of the approving manager

#     Returns:
#         Updated ExpenseClaim in APPROVED status with approval details

#     Note:
#         This is a thin delegation layer. All approval logic, status validation,
#         and state transitions are managed by the ExpenseClaimService.
#     """
#     return expense_claim_service.approve_claim(
#         claim_id=claim_id,
#         approver_id=approver_id,
#         approver_name=approver_name,
#     )


# @tool
# def reject_claim(
#     claim_id: ClaimId,
#     approver_id: EmployeeId,
#     approver_name: str,
#     reason: str,
# ) -> ExpenseClaim:
#     """
#     Reject an expense claim.

#     This tool delegates to ExpenseClaimService.reject_claim() to transition
#     a claim to REJECTED status and record the rejection decision with reason.

#     Args:
#         claim_id: ClaimId of the claim to reject
#         approver_id: EmployeeId of the rejecting manager
#         approver_name: Full name of the rejecting manager
#         reason: Reason for rejection (communicated to employee)

#     Returns:
#         Updated ExpenseClaim in REJECTED status with rejection details

#     Note:
#         This is a thin delegation layer. All rejection logic, status validation,
#         and state transitions are managed by the ExpenseClaimService.
#     """
#     return expense_claim_service.reject_claim(
#         claim_id=claim_id,
#         approver_id=approver_id,
#         approver_name=approver_name,
#         reason=reason,
#     )


# @tool
# def list_pending_claims() -> list[ExpenseClaim]:
#     """
#     List all pending expense claims awaiting approval.

#     This tool delegates to ExpenseClaimService.list_pending_claims() to retrieve
#     all claims in SUBMITTED status that require manager review.

#     Returns:
#         List of ExpenseClaim aggregates in SUBMITTED status, ordered by
#         submission date (newest first)

#     Note:
#         This is a thin delegation layer. All query logic and filtering
#         is managed by the ExpenseClaimService.
#     """
#     return expense_claim_service.list_pending_claims()


# @tool
# def list_manager_queue(
#     manager_id: EmployeeId,
# ) -> list[ExpenseClaim]:
#     """
#     List all claims assigned to a specific manager for approval.

#     This tool delegates to ExpenseClaimService.list_manager_queue() to retrieve
#     all claims awaiting approval by a particular manager.

#     Args:
#         manager_id: EmployeeId of the manager whose queue to retrieve

#     Returns:
#         List of ExpenseClaim aggregates assigned to the manager for approval,
#         ordered by submission date (newest first)

#     Note:
#         This is a thin delegation layer. All queue filtering and query
#         logic is managed by the ExpenseClaimService.
#     """
#     return expense_claim_service.list_manager_queue(manager_id)

from __future__ import annotations

from strands import tool

from models.expense_claim import ExpenseClaim
from services.expense_claim_service import ExpenseClaimService

expense_claim_service = ExpenseClaimService()


@tool
def approve_claim(
    claim_id: str,
    approver_id: str,
    approver_name: str,
) -> ExpenseClaim:
    """
    Approve an expense claim.
    """
    return expense_claim_service.approve_claim(
        claim_id=claim_id,
        approver_id=approver_id,
        approver_name=approver_name,
    )


@tool
def reject_claim(
    claim_id: str,
    approver_id: str,
    approver_name: str,
    reason: str,
) -> ExpenseClaim:
    """
    Reject an expense claim.
    """
    return expense_claim_service.reject_claim(
        claim_id=claim_id,
        approver_id=approver_id,
        approver_name=approver_name,
        reason=reason,
    )


@tool
def list_pending_claims() -> list[ExpenseClaim]:
    """
    Retrieve all pending expense claims.
    """
    return expense_claim_service.list_pending_claims()


@tool
def list_manager_queue(
    manager_id: str,
) -> list[ExpenseClaim]:
    """
    Retrieve the approval queue for a manager.
    """
    return expense_claim_service.list_manager_queue(manager_id)
