# """
# Expense Tools for AI Agents.

# This module provides native Strands tools that delegate expense claim operations to the
# ExpenseClaimService. These tools are designed for use by AI agents and follow the
# Strands Agents SDK pattern.

# Tools are thin delegation layers that:
# - Call exactly one service method
# - Do not contain business logic
# - Do not access repositories directly
# - Use existing DTOs and exception handling
# - Follow project logging and typing conventions
# """

# from __future__ import annotations

# from strands import tool

# from services.expense_claim_service import ExpenseClaimService
# from models.dto.submit_claim import SubmitExpenseClaimRequest
# from models.dto.claim_preview import ClaimPreview
# from models.expense_claim import ExpenseClaim
# from common.identifiers import ClaimId

# # Shared service instance for all tools in this module
# expense_claim_service = ExpenseClaimService()


# @tool
# def preview_claim(
#     request: SubmitExpenseClaimRequest,
# ) -> ClaimPreview:
#     """
#     Preview an expense claim without persisting it.

#     This tool delegates to ExpenseClaimService.preview_claim() to calculate
#     reimbursement amounts and policy compliance for a claim submission.

#     Args:
#         request: SubmitExpenseClaimRequest DTO containing claim details

#     Returns:
#         ClaimPreview DTO with calculated totals and validation results

#     Note:
#         This is a thin delegation layer. All validation and business logic
#         is handled by the ExpenseClaimService.
#     """
#     return expense_claim_service.preview_claim(request)


# @tool
# def submit_claim(
#     request: SubmitExpenseClaimRequest,
# ) -> ExpenseClaim:
#     """
#     Submit a new expense claim for processing.

#     This tool delegates to ExpenseClaimService.submit_claim() to validate,
#     calculate, and persist a new expense claim.

#     Args:
#         request: SubmitExpenseClaimRequest DTO containing claim details

#     Returns:
#         Persisted ExpenseClaim in SUBMITTED status

#     Note:
#         This is a thin delegation layer. All validation, calculation,
#         and persistence logic is handled by the ExpenseClaimService.
#     """
#     return expense_claim_service.submit_claim(request)


# @tool
# def get_claim(
#     claim_id: ClaimId,
# ) -> ExpenseClaim:
#     """
#     Retrieve an existing expense claim by identifier.

#     This tool delegates to ExpenseClaimService.get_claim() to fetch
#     a persisted expense claim.

#     Args:
#         claim_id: ClaimId of the claim to retrieve

#     Returns:
#         ExpenseClaim aggregate with full claim details

#     Note:
#         This is a thin delegation layer. All retrieval logic and
#         error handling is managed by the ExpenseClaimService.
#     """
#     return expense_claim_service.get_claim(claim_id)


from strands import tool

from models.dto.claim_preview import ClaimPreview
from models.dto.submit_claim import SubmitExpenseClaimRequest
from models.expense_claim import ExpenseClaim
from services.expense_claim_service import ExpenseClaimService

expense_claim_service = ExpenseClaimService()


@tool
def preview_claim(
    request: SubmitExpenseClaimRequest,
) -> ClaimPreview:
    """
    Generate a reimbursement preview for an expense claim.

    Args:
        request:
            Claim submission request.

    Returns:
        ClaimPreview containing calculated reimbursement details.
    """
    return expense_claim_service.preview_claim(request)


@tool
def submit_claim(
    request: SubmitExpenseClaimRequest,
) -> ExpenseClaim:
    """
    Submit a new expense claim.

    Args:
        request:
            Claim submission request.

    Returns:
        Persisted ExpenseClaim.
    """
    return expense_claim_service.submit_claim(request)


@tool
def get_claim(
    claim_id: str,
) -> ExpenseClaim:
    """
    Retrieve an expense claim.

    Args:
        claim_id:
            Business claim identifier.

    Returns:
        ExpenseClaim aggregate.
    """
    return expense_claim_service.get_claim(claim_id)
