"""
Expense Claim Service.

Core business workflow for processing travel expense claims.

Responsibilities
----------------
- Employee validation
- Expense category validation
- Policy lookup
- Reimbursement calculation
- Receipt validation
- Approval determination
- Claim persistence
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from common.identifiers import (
    ClaimId,
    EmployeeId,
)
from config.enums import ClaimStatus
from exceptions.repository import RepositoryException
from models.claim_amount import ClaimAmount
from models.dto.claim_preview import (
    ClaimPreview,
    ExpenseItemResult,
)
from models.dto.expense_item import ExpenseItem
from models.dto.submit_claim import (
    SubmitExpenseClaimRequest,
)
from models.employee import Employee
from models.expense_claim import ExpenseClaim
from repositories.expense_claim_repository import (
    ExpenseClaimRepository,
)
from services.base import BaseService
from services.employee_service import EmployeeService
from services.expense_category_service import (
    ExpenseCategoryService,
)
from services.expense_policy_service import (
    ExpensePolicyService,
)
from services.receipt_service import (
    ReceiptService,
)


class ExpenseClaimService(BaseService):
    """
    Core business workflow.

    Coordinates all business services required
    to process travel expense reimbursement.
    """

    def __init__(self) -> None:

        super().__init__()

        self.claim_repository = ExpenseClaimRepository()

        self.employee_service = EmployeeService()

        self.category_service = ExpenseCategoryService()

        self.policy_service = ExpensePolicyService()

        self.receipt_service = ReceiptService()
        
    
    ###########################################################################
    # Public API
    ###########################################################################

    def preview_claim(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> ClaimPreview:
        """
        Calculate reimbursement preview.

        Nothing is persisted.
        """
        self.log_start("Preview Claim")

        # Validate employee
        employee = self._validate_employee(request)

        # Validate expense items
        self._validate_items(request)

        # Calculate claim
        items = self._calculate_claim(employee, request)

        # Build preview
        preview = self._build_preview(employee, request, items)

        self.log_success("Preview Claim")

        return preview

    def submit_claim(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> ExpenseClaim:
        """
        Persist a validated claim.
        """
        self.log_start("Submit Claim")

        # Validate employee
        employee = self._validate_employee(request)

        # Validate expense items
        self._validate_items(request)

        # Calculate claim
        items = self._calculate_claim(employee, request)

        # Build preview
        preview = self._build_preview(employee, request, items)

        # Persist claim
        claim = self._persist_claim(request, preview)

        self.log_success("Submit Claim")

        return claim

    def approve_claim(
        self,
        claim_id: ClaimId,
    ) -> ExpenseClaim:
        """
        Approve an expense claim.
        """
        self.log_start("Approve Claim")

        # Get the claim
        claim = self.get_claim(claim_id)

        # Validate claim can be approved
        if claim.status != ClaimStatus.UNDER_REVIEW:
            raise RepositoryException(
                message=f"Claim '{claim_id}' cannot be approved in status '{claim.status.value}'."
            )

        # Approve the claim
        claim.approve(
            approver_id="system",  # TODO: Get from context
            approver_name="System Approver"  # TODO: Get from context
        )

        # Save the claim
        updated_claim = self.claim_repository.save(claim)

        self.log_success("Approve Claim")

        return updated_claim

    def reject_claim(
        self,
        claim_id: ClaimId,
        reason: str,
    ) -> ExpenseClaim:
        """
        Reject an expense claim.
        """
        self.log_start("Reject Claim")

        # Get the claim
        claim = self.get_claim(claim_id)

        # Validate claim can be rejected
        if claim.status != ClaimStatus.UNDER_REVIEW:
            raise RepositoryException(
                message=f"Claim '{claim_id}' cannot be rejected in status '{claim.status.value}'."
            )

        # Reject the claim
        claim.reject(
            approver_id="system",  # TODO: Get from context
            approver_name="System Approver",  # TODO: Get from context
            reason=reason
        )

        # Save the claim
        updated_claim = self.claim_repository.save(claim)

        self.log_success("Reject Claim")

        return updated_claim

    def get_claim(
        self,
        claim_id: ClaimId,
    ) -> ExpenseClaim:
        """
        Retrieve a claim.
        """
        raise NotImplementedError

    def list_employee_claims(
        self,
        employee_id: EmployeeId,
    ) -> list[ExpenseClaim]:
        """
        Return all claims for an employee.
        """
        raise NotImplementedError

    def list_pending_claims(
        self,
    ) -> list[ExpenseClaim]:
        """
        Return all pending claims.
        """
        raise NotImplementedError

    def list_manager_queue(
        self,
        manager_id: EmployeeId,
    ) -> list[ExpenseClaim]:
        """
        Return manager approval queue.
        """
        raise NotImplementedError
    
    ###########################################################################
    # Validation
    ###########################################################################

    def _validate_employee(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> Employee:
        """
        Validate employee.
        """
        raise NotImplementedError

    def _validate_items(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> None:
        """
        Validate expense items.
        """
        raise NotImplementedError

    ###########################################################################
    # Calculation
    ###########################################################################

    def _calculate_item(
        self,
        employee: Employee,
        item: ExpenseItem,
    ) -> ExpenseItemResult:
        """
        Calculate one expense item.
        """
        # Check if receipt is required
        try:
            receipt_required = self.policy_service.receipt_required(
                category_id=item.category_code,
                employee_grade=employee.grade
            )
        except RepositoryException:
            # If no specific policy, use default approval
            return ExpenseItemResult(
                category=item.category_code,
                requested_amount=item.requested_amount,
                approved_amount=item.requested_amount,
                receipt_required=False,
                approval_required=False,
                status="APPROVED",
                reason=None
            )

        # Check if approval is required
        approval_required = self.policy_service.approval_required(
            category_id=item.category_code,
            employee_grade=employee.grade
        )

        # For now, approve the full amount (simplified logic)
        # In future, add proper policy validation
        approved_amount = item.requested_amount
        status = "APPROVED"
        reason = None

        # Check if receipt is required but not provided
        if receipt_required and not item.receipt_available:
            status = "REJECTED"
            reason = "Receipt required but not provided"
            approved_amount = Decimal("0")

        return ExpenseItemResult(
            category=item.category_code,
            requested_amount=item.requested_amount,
            approved_amount=approved_amount,
            receipt_required=receipt_required,
            approval_required=approval_required,
            status=status,
            reason=reason
        )

    def _calculate_claim(
        self,
        employee: Employee,
        request: SubmitExpenseClaimRequest,
    ) -> list[ExpenseItemResult]:
        """
        Calculate entire claim.
        """
        results = []
        
        for item in request.expense_items:
            result = self._calculate_item(employee, item)
            results.append(result)
        
        return results

    ###########################################################################
    # Preview
    ###########################################################################

    def _build_preview(
        self,
        employee: Employee,
        request: SubmitExpenseClaimRequest,
        items: list[ExpenseItemResult],
    ) -> ClaimPreview:
        """
        Build preview response.
        """
        # Calculate totals
        total_requested = sum(item.requested_amount for item in items)
        total_approved = sum(item.approved_amount for item in items)
        
        # Check if any item requires approval
        approval_required = any(item.approval_required for item in items)
        
        # Build warnings
        warnings = []
        for item in items:
            if item.status == "REJECTED" and item.reason:
                warnings.append(f"{item.category}: {item.reason}")
        
        return ClaimPreview(
            employee_id=employee.employee_id,
            employee_name=f"{employee.first_name} {employee.last_name}",
            employee_grade=employee.grade,
            total_requested=total_requested,
            total_approved=total_approved,
            approval_required=approval_required,
            items=items,
            warnings=warnings
        )

    ###########################################################################
    # Persistence
    ###########################################################################

    def _persist_claim(
        self,
        request: SubmitExpenseClaimRequest,
        preview: ClaimPreview,
    ) -> ExpenseClaim:
        """
        Persist claim.
        """
        # Create the claim entity
        claim = ExpenseClaim(
            claim_id=(
                f"CLM{request.employee_id[3:]}{int(datetime.now().timestamp())}"
            ),  # Simple ID generation
            employee_id=request.employee_id,
            employee_name=preview.employee_name,
            department="",  # TODO: Get from employee or request
            trip_id=None,  # TODO: Add trip management
            business_purpose=(
                f"Business trip to {request.destination} "
                f"from {request.trip_start_date} to {request.trip_end_date}"
            ),
            expense_category=(
                self.category_service.get_category(
                    request.expense_items[0].category_code
                )
                if request.expense_items
                else None
            ),
            expense_date=request.trip_start_date,
            submitted_at=datetime.now(),
            status=ClaimStatus.SUBMITTED,
            amount=ClaimAmount(
                claimed_amount=preview.total_requested,
                reimbursable_amount=preview.total_approved
            ),
            approval=None,  # Will be set during approval
            validation=None,  # Will be set during validation
            receipts=[],  # Will be added separately
            policy_id=None,  # TODO: Add policy management
            notes=request.comments
        )
        
        # Save the claim
        return self.claim_repository.save(claim)
    
    def _validate_employee(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> Employee:
        """
        Validate the employee submitting the claim.
        """

        self.log_start("Validate Employee")

        employee = self.employee_service.get_employee(
            request.employee_id,
        )

        if not employee.is_active:
            raise RepositoryException(
                message=(
                    f"Employee '{employee.employee_id}' "
                    "is inactive."
                ),
            )

        self.log_success("Validate Employee")

        return employee
    
    def _validate_items(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> None:
        """
        Validate submitted expense items.
        """

        self.log_start("Validate Expense Items")

        if not request.expense_items:

            raise RepositoryException(
                message="At least one expense item is required.",
            )

        for item in request.expense_items:

            if item.requested_amount <= Decimal("0"):

                raise RepositoryException(
                    message=(
                        "Expense amount must be greater than zero."
                    ),
                )

        self.log_success("Validate Expense Items")
        
    def get_claim(
        self,
        claim_id: ClaimId,
    ) -> ExpenseClaim:
        """
        Retrieve a claim.
        """

        self.log_start("Get Expense Claim")

        claim = self.claim_repository.get_claim(
            claim_id,
        )

        if claim is None:

            raise RepositoryException(
                message=f"Claim '{claim_id}' does not exist.",
            )

        self.log_success("Get Expense Claim")

        return claim
    

    def list_employee_claims(
        self,
        employee_id: EmployeeId,
    ) -> list[ExpenseClaim]:
        """
        Return claims submitted by an employee.
        """

        self.log_start("List Employee Claims")

        claims = (
            self.claim_repository.list_employee_claims(
                employee_id,
            )
        )

        self.log_success("List Employee Claims")

        return claims
    
    def list_pending_claims(
        self,
    ) -> list[ExpenseClaim]:
        """
        Return pending claims.
        """

        self.log_start("List Pending Claims")

        claims = (
            self.claim_repository.list_pending_claims()
        )

        self.log_success("List Pending Claims")

        return claims