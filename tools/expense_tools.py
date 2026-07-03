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


def _normalize_request(request):
    if isinstance(request, dict):
        return SubmitExpenseClaimRequest.model_validate(request)
    return request


@tool
def preview_claim(
    request: SubmitExpenseClaimRequest | dict,
) -> ClaimPreview:
    """
    Generate a reimbursement preview for an expense claim.

    Args:
        request:
            Claim submission request.

    Returns:
        ClaimPreview containing calculated reimbursement details.
    """
    request = _normalize_request(request)

    return expense_claim_service.preview_claim(request)


@tool
def submit_claim(
    request: SubmitExpenseClaimRequest | dict,
) -> ExpenseClaim:
    """
    Submit a new expense claim.

    Args:
        request:
            Claim submission request.

    Returns:
        Persisted ExpenseClaim.
    """
    request = _normalize_request(request)

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


@tool
def validate_policy_compliance(
    claim_id: str,
) -> dict:
    """
    Validate policy compliance for a claim.

    Args:
        claim_id:
            Business claim identifier.

    Returns:
        Policy compliance validation results.
    """
    return expense_claim_service.validate_policy_compliance(claim_id)


@tool
def detect_duplicate_claims(
    employee_id: str,
    trip_name: str,
    trip_start_date: str,
    trip_end_date: str,
) -> list[ExpenseClaim]:
    """
    Detect potential duplicate claims.

    Args:
        employee_id:
            Employee identifier.
        trip_name:
            Trip name.
        trip_start_date:
            Trip start date (YYYY-MM-DD).
        trip_end_date:
            Trip end date (YYYY-MM-DD).

    Returns:
        List of potential duplicate claims.
    """
    from datetime import datetime

    start_date = datetime.fromisoformat(trip_start_date).date()
    end_date = datetime.fromisoformat(trip_end_date).date()
    return expense_claim_service.detect_duplicate_claims(
        employee_id, trip_name, start_date, end_date
    )


@tool
def calculate_reimbursement(
    claim_id: str,
) -> dict:
    """
    Calculate reimbursement for a claim.

    Args:
        claim_id:
            Business claim identifier.

    Returns:
        Reimbursement calculation details.
    """
    return expense_claim_service.calculate_reimbursement(claim_id)


@tool
def calculate_variance(
    claim_id: str,
) -> dict:
    """
    Calculate variance between claimed and approved amounts.

    Args:
        claim_id:
            Business claim identifier.

    Returns:
        Variance calculation results.
    """
    return expense_claim_service.calculate_variance(claim_id)


@tool
def get_claim_status(
    claim_id: str,
) -> dict:
    """
    Retrieve detailed status information for a claim.

    Args:
        claim_id:
            Business claim identifier.

    Returns:
        Claim status details.
    """
    return expense_claim_service.get_claim_status(claim_id)
