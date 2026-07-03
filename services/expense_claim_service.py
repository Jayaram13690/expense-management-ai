"""
Expense Claim Service.

Core business workflow for processing travel expense claims.

Responsibilities
----------------
Service (this layer)
    - Orchestration: coordinates employee, category, and policy services
    - Input validation: employee activity, trip dates, expense date bounds
    - Repository interaction: delegates all persistence to claim_repository
    - DTO translation: ExpenseItem -> ExpenseLineItem, ExpenseLineItem -> ExpenseItemResult

Aggregate (ExpenseClaim)
    - Business behaviour and lifecycle transitions
    - Aggregate invariants (enforced inside the aggregate)
    - Owns all internal state mutations (ClaimAmount, Approval, status)

Value Objects (ExpenseLineItem, ClaimAmount, Approval)
    - Immutable business concepts and calculations

Repository (ExpenseClaimRepository)
    - Persistence only, no business logic

DTOs (SubmitExpenseClaimRequest, ClaimPreview, ExpenseItemResult)
    - Transport shapes, never persisted

Architecture
------------
Input DTOs are consumed at the service boundary.
Domain value objects are constructed by the service and handed to the aggregate.
Output DTOs are produced by the service from domain state.
No DTO crosses the persistence boundary.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pprint import pprint
from uuid import uuid4

from common.identifiers import ClaimId, EmployeeId
from config.enums import ClaimStatus
from exceptions.service import ServiceException
from models.claim_amount import ClaimAmount
from models.dto.claim_preview import ClaimPreview, ExpenseItemResult
from models.dto.expense_item import ExpenseItem
from models.dto.submit_claim import SubmitExpenseClaimRequest
from models.employee import Employee
from models.expense_claim import ExpenseClaim
from models.expense_line_item import ExpenseLineItem, LineItemStatus
from repositories.expense_claim_repository import ExpenseClaimRepository
from services.base import BaseService
from services.employee_service import EmployeeService
from services.expense_category_service import ExpenseCategoryService
from services.expense_policy_service import ExpensePolicyService


def _generate_claim_id() -> str:
    """
    Generate a collision-resistant unique business identifier for a new claim.

    Produces a CLM-prefixed identifier using the first 12 hexadecimal
    characters of a UUID4.  UUID4 is cryptographically random, making
    collisions statistically negligible even under high concurrency.

    The result satisfies the ClaimId pattern ``^CLM\\d{4,12}$`` by converting
    the UUID hex to an integer and taking the last 12 digits, ensuring
    the numeric portion is always exactly 12 digits.

    Returns:
        A unique ClaimId string in the format CLMxxxxxxxxxxxx (12 digits).
    """
    uid = uuid4().int % (10**12)
    return f"CLM{uid:012d}"


class ExpenseClaimService(BaseService):
    """
    Service responsible for the expense claim business workflow.

    Orchestrates employee validation, trip and item validation,
    policy calculation, aggregate construction, persistence, and
    approval lifecycle transitions.

    This service does NOT manipulate aggregate-internal value objects
    directly.  All state mutations are delegated to aggregate methods.
    """

    def __init__(self) -> None:
        super().__init__()

        self.claim_repository = ExpenseClaimRepository()
        self.employee_service = EmployeeService()
        self.category_service = ExpenseCategoryService()
        self.policy_service = ExpensePolicyService()

    ###########################################################################
    # Public API
    ###########################################################################

    def preview_claim(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> ClaimPreview:
        """
        Calculate a reimbursement preview without persisting anything.

        Validates the employee, trip dates, and all expense items, then
        runs policy calculation for each item.  Returns a ClaimPreview DTO
        with a per-item breakdown and aggregate totals.  Nothing is written
        to the database.

        Args:
            request:
                Claim submission request from the caller.

        Returns:
            ClaimPreview DTO containing per-item results and totals.

        Raises:
            ServiceException:
                If the employee is invalid, trip dates are inconsistent,
                any expense date falls outside the trip period, or a
                required category or policy is not found.
        """
        self.log_start("Preview Expense Claim")
        # print(type(request))
        # print(request)

        employee = self._validate_employee(request)
        self._validate_trip_dates(request)
        self._validate_items(request)

        duplicates = self.detect_duplicate_claims(
            employee_id=request.employee_id,
            trip_name=request.trip_name,
            trip_start_date=request.trip_start_date,
            trip_end_date=request.trip_end_date,
        )
        if duplicates:
            raise ServiceException(
                message="Expense claim already exists for this employee and trip.",
                error_code="CLAIM_ALREADY_EXISTS",
            )

        line_items = self._calculate_line_items(employee, request)
        preview = self._build_preview(employee, line_items, request)

        self.log_success("Preview Expense Claim")
        return preview

    def submit_claim(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> ExpenseClaim:
        """
        Submit a new expense claim.

        Validates the employee, trip dates, and all expense items, calculates
        per-item reimbursements against applicable policies, constructs the
        ExpenseClaim aggregate with validated line items, and persists it.

        The claim is transitioned to SUBMITTED status by the aggregate before
        persistence.

        Args:
            request:
                Claim submission request from the caller.

        Returns:
            Persisted ExpenseClaim in SUBMITTED status.

        Raises:
            ServiceException:
                If the employee is invalid, trip dates are inconsistent,
                any expense date falls outside the trip period, or a
                required category or policy is not found.
        """
        self.log_start("Submit Expense Claim")
        # print(type(request))
        # print(request)

        employee = self._validate_employee(request)
        self._validate_trip_dates(request)
        self._validate_items(request)

        duplicates = self.detect_duplicate_claims(
            employee_id=request.employee_id,
            trip_name=request.trip_name,
            trip_start_date=request.trip_start_date,
            trip_end_date=request.trip_end_date,
        )
        if duplicates:
            raise ServiceException(
                message="Expense claim already exists for this employee and trip.",
                error_code="CLAIM_ALREADY_EXISTS",
            )

        line_items = self._calculate_line_items(employee, request)
        claim = self._build_claim(employee, request, line_items)
        self._persist_claim(claim)

        self.log_success("Submit Expense Claim")
        return claim

    def approve_claim(
        self,
        claim_id: ClaimId,
        approver_id: EmployeeId,
        approver_name: str,
    ) -> ExpenseClaim:
        """
        Approve an expense claim.

        Delegates all state transitions to the aggregate via
        ``claim.finalize_approval()``.  The aggregate internally updates
        the Approval value object, finalises the ClaimAmount reimbursable
        total, and transitions to APPROVED status.

        Args:
            claim_id:
                Identifier of the claim to approve.

            approver_id:
                Employee ID of the approving manager.

            approver_name:
                Full name of the approving manager.

        Returns:
            Updated ExpenseClaim in APPROVED status.

        Raises:
            ServiceException:
                If the claim does not exist.

            ValueError:
                If the claim's current status does not allow approval
                (enforced by the aggregate).
        """
        self.log_start("Approve Expense Claim")

        claim = self._fetch_claim(claim_id)
        claim.finalize_approval(approver_id, approver_name)
        self.claim_repository.save(claim)

        self.log_success("Approve Expense Claim")
        return claim

    def reject_claim(
        self,
        claim_id: ClaimId,
        approver_id: EmployeeId,
        approver_name: str,
        reason: str,
    ) -> ExpenseClaim:
        """
        Reject an expense claim.

        Delegates all state transitions to the aggregate via
        ``claim.finalize_rejection()``.  The aggregate internally updates
        the Approval value object and transitions to REJECTED status.

        Args:
            claim_id:
                Identifier of the claim to reject.

            approver_id:
                Employee ID of the rejecting manager.

            approver_name:
                Full name of the rejecting manager.

            reason:
                Reason for rejection, communicated back to the employee.

        Returns:
            Updated ExpenseClaim in REJECTED status.

        Raises:
            ServiceException:
                If the claim does not exist.

            ValueError:
                If the claim's current status does not allow rejection
                (enforced by the aggregate).
        """
        self.log_start("Reject Expense Claim")

        claim = self._fetch_claim(claim_id)
        claim.finalize_rejection(approver_id, approver_name, reason)
        self.claim_repository.save(claim)

        self.log_success("Reject Expense Claim")
        return claim

    def get_claim(
        self,
        claim_id: ClaimId,
    ) -> ExpenseClaim:
        """
        Retrieve an expense claim by identifier.

        Args:
            claim_id:
                The claim identifier.

        Returns:
            ExpenseClaim aggregate.

        Raises:
            ServiceException: If the claim does not exist.
        """
        self.log_start("Get Expense Claim")

        claim = self._fetch_claim(claim_id)

        self.log_success("Get Expense Claim")
        return claim

    def list_employee_claims(
        self,
        employee_id: EmployeeId,
    ) -> list[ExpenseClaim]:
        """
        Return all claims submitted by a given employee.

        Args:
            employee_id:
                Identifier of the employee.

        Returns:
            List of ExpenseClaim aggregates.
        """
        self.log_start("List Employee Claims")

        claims = self.claim_repository.list_employee_claims(employee_id)

        self.log_success("List Employee Claims")
        return claims

    def list_pending_claims(self) -> list[ExpenseClaim]:
        """
        Return all claims in SUBMITTED status awaiting manager review.

        Returns:
            List of submitted ExpenseClaim aggregates.
        """
        self.log_start("List Pending Claims")

        claims = self.claim_repository.list_claims_by_status(
            ClaimStatus.SUBMITTED,
        )

        self.log_success("List Pending Claims")
        return claims

    def list_manager_queue(
        self,
        manager_id: EmployeeId,
    ) -> list[ExpenseClaim]:
        """
        Return all submitted claims assigned to a manager for approval.

        Args:
            manager_id:
                Employee ID of the manager.

        Returns:
            List of ExpenseClaim aggregates awaiting this manager's decision.
        """
        self.log_start("List Manager Queue")

        claims = self.claim_repository.list_manager_queue(
            approver_id=manager_id,
            status=ClaimStatus.SUBMITTED,
        )

        self.log_success("List Manager Queue")
        return claims

    ###########################################################################
    # Validation — Service Responsibilities
    ###########################################################################

    def _validate_employee(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> Employee:
        """
        Validate that the employee submitting the claim exists and is active.

        Existence checking is delegated to EmployeeService, which raises
        RepositoryException if the employee is not found.

        Args:
            request:
                The claim submission request.

        Returns:
            Validated Employee entity.

        Raises:
            RepositoryException: If the employee does not exist.
            ServiceException: If the employee is inactive.
        """
        employee = self.employee_service.get_employee(request.employee_id)

        if not employee.is_active:
            raise ServiceException(
                message=(
                    f"Employee '{employee.employee_id}' is inactive "
                    "and cannot submit expense claims."
                ),
                error_code="EMPLOYEE_INACTIVE",
            )

        return employee

    def _validate_trip_dates(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> None:
        """
        Validate trip date consistency.

        Checks that trip_end_date is not before trip_start_date.
        The aggregate enforces this invariant at construction time, but
        we validate here to raise a ServiceException with a clear error
        code before attempting construction.

        Args:
            request:
                The claim submission request.

        Raises:
            ServiceException: If trip_end_date precedes trip_start_date.
        """
        if request.trip_end_date < request.trip_start_date:
            raise ServiceException(
                message=(
                    f"trip_end_date '{request.trip_end_date}' cannot be "
                    f"before trip_start_date '{request.trip_start_date}'."
                ),
                error_code="INVALID_TRIP_DATES",
            )

    def _validate_items(
        self,
        request: SubmitExpenseClaimRequest,
    ) -> None:
        """
        Validate all expense items in the submission request.

        Checks that each item's amount is positive and that each
        expense_date falls within the declared trip period
        (trip_start_date … trip_end_date, inclusive).

        The DTO already enforces min_length=1 on expense_items, so
        an empty list is prevented at the DTO level.

        Args:
            request:
                The claim submission request.

        Raises:
            ServiceException: If any item fails validation.
        """
        for item in request.expense_items:
            if item.requested_amount <= Decimal("0"):
                raise ServiceException(
                    message=(
                        f"Expense amount must be greater than zero "
                        f"for category '{item.category_code}'."
                    ),
                    error_code="INVALID_EXPENSE_AMOUNT",
                )

            if item.expense_date < request.trip_start_date:
                raise ServiceException(
                    message=(
                        f"Expense date '{item.expense_date}' for category "
                        f"'{item.category_code}' is before the trip start "
                        f"date '{request.trip_start_date}'."
                    ),
                    error_code="EXPENSE_DATE_BEFORE_TRIP",
                )

            if item.expense_date > request.trip_end_date:
                raise ServiceException(
                    message=(
                        f"Expense date '{item.expense_date}' for category "
                        f"'{item.category_code}' is after the trip end "
                        f"date '{request.trip_end_date}'."
                    ),
                    error_code="EXPENSE_DATE_AFTER_TRIP",
                )

    ###########################################################################
    # Calculation
    ###########################################################################

    def _calculate_item(
        self,
        employee: Employee,
        item: ExpenseItem,
    ) -> ExpenseLineItem:
        """
        Calculate reimbursement for a single expense item DTO.

        Looks up the expense category and the applicable policy for this
        employee's grade, then applies business rules to determine the
        approved amount and line-item status.

        Receipt validation at this stage is based on the employee's
        declaration (``item.receipt_available``).  Physical receipt
        verification happens separately when receipts are uploaded and
        linked to the persisted claim via ReceiptService.

        This is the only place where an input DTO (ExpenseItem) is
        translated into a domain value object (ExpenseLineItem).

        Args:
            employee:
                The employee submitting the expense.

            item:
                Input expense item DTO from the submission request.

        Returns:
            A fully calculated ExpenseLineItem domain value object.

        Raises:
            ServiceException:
                If the category does not exist, no active policy is found,
                or the policy is not effective on the expense date.
        """
        category = self.category_service.get_category_by_code(
            item.category_code,
        )

        policy = self.policy_service.get_policy(
            category_id=category.category_id,
            employee_grade=employee.grade,
        )

        if not policy.is_effective(item.expense_date):
            raise ServiceException(
                message=(
                    f"No active policy for category '{item.category_code}' "
                    f"on expense date '{item.expense_date}'."
                ),
                error_code="POLICY_NOT_EFFECTIVE",
            )

        approved_amount = min(item.requested_amount, policy.daily_limit)
        status = LineItemStatus.APPROVED
        remarks: str | None = None

        if approved_amount < item.requested_amount:
            status = LineItemStatus.PARTIALLY_APPROVED
            remarks = (
                f"Claimed amount exceeds the policy daily limit of "
                f"{policy.daily_limit} {policy.currency}. "
                f"Approved amount capped at {approved_amount} {policy.currency}."
            )

        return ExpenseLineItem(
            category_code=category.category_code,
            category_name=category.category_name,
            expense_date=item.expense_date,
            claimed_amount=item.requested_amount,
            approved_amount=approved_amount,
            currency=item.currency,
            receipt_required=policy.receipt_required,
            approval_required=policy.approval_required,
            status=status,
            remarks=remarks,
        )

    def _calculate_line_items(
        self,
        employee: Employee,
        request: SubmitExpenseClaimRequest,
    ) -> list[ExpenseLineItem]:
        """
        Calculate reimbursement for every expense item in the request.

        Delegates to ``_calculate_item()`` for each item and collects
        results in submission order.

        Args:
            employee:
                The employee submitting the claim.

            request:
                The claim submission request.

        Returns:
            Ordered list of calculated ExpenseLineItem value objects.
        """
        return [self._calculate_item(employee, item) for item in request.expense_items]

    ###########################################################################
    # Claim Construction
    ###########################################################################

    def _build_claim(
        self,
        employee: Employee,
        request: SubmitExpenseClaimRequest,
        line_items: list[ExpenseLineItem],
    ) -> ExpenseClaim:
        """
        Construct and submit an ExpenseClaim aggregate from validated data.

        Assembles the aggregate root with all trip context and attaches
        the validated line items.  The aggregate-level ClaimAmount is
        populated from the computed line-item totals.  The aggregate's
        ``submit()`` method is called to enforce the submission invariant
        and transition to SUBMITTED status.

        Args:
            employee:
                Validated employee entity.

            request:
                Claim submission request DTO.

            line_items:
                Calculated ExpenseLineItem value objects.

        Returns:
            A fully constructed ExpenseClaim in SUBMITTED status,
            ready for persistence.
        """
        total_claimed = sum(
            (item.claimed_amount for item in line_items),
            start=Decimal("0.00"),
        )

        total_approved = sum(
            (item.approved_amount for item in line_items),
            start=Decimal("0.00"),
        )

        currency = line_items[0].currency if line_items else "INR"

        claim = ExpenseClaim(
            claim_id=_generate_claim_id(),
            employee_id=employee.employee_id,
            employee_name=employee.full_name,
            employee_grade=employee.grade,
            department=employee.department,
            trip_name=request.trip_name,
            business_purpose=request.business_purpose,
            destination=request.destination,
            trip_start_date=request.trip_start_date,
            trip_end_date=request.trip_end_date,
            expense_line_items=line_items,
            amount=ClaimAmount(
                claimed_amount=total_claimed,
                approved_amount=total_approved,
                reimbursable_amount=total_approved,
                currency=currency,
            ),
            notes=request.comments,
        )

        claim.submit()
        return claim

    def validate_policy_compliance(
        self,
        claim_id: ClaimId,
    ) -> dict:
        """
        Validate policy compliance for an existing claim.
        """
        self.log_start("Validate Policy Compliance")

        claim = self._fetch_claim(claim_id)
        compliance_results = []

        for item in claim.expense_line_items:
            compliance_result = {
                "category": item.category_name,
                "claimed_amount": item.claimed_amount,
                "approved_amount": item.approved_amount,
                "compliant": item.status == LineItemStatus.APPROVED,
                "reason": item.remarks if not item.remarks else "Policy compliant",
            }
            compliance_results.append(compliance_result)

        self.log_success("Validate Policy Compliance")
        return {"claim_id": claim_id, "compliance_results": compliance_results}

    def detect_duplicate_claims(
        self,
        employee_id: EmployeeId,
        trip_name: str,
        trip_start_date: date,
        trip_end_date: date,
    ) -> list[ExpenseClaim]:
        """
        Detect potential duplicate claims.
        """
        self.log_start("Detect Duplicate Claims")

        # Get all claims for the employee
        employee_claims = self.list_employee_claims(employee_id)

        # Filter for claims with similar trip details
        duplicates = []
        for claim in employee_claims:
            if (
                claim.trip_name == trip_name
                and claim.trip_start_date == trip_start_date
                and claim.trip_end_date == trip_end_date
                and claim.status != ClaimStatus.REJECTED
            ):
                duplicates.append(claim)

        self.log_success("Detect Duplicate Claims")
        return duplicates

    def calculate_reimbursement(
        self,
        claim_id: ClaimId,
    ) -> dict:
        """
        Calculate reimbursement amount for a claim.
        """
        self.log_start("Calculate Reimbursement")

        claim = self._fetch_claim(claim_id)

        total_reimbursement = claim.amount.reimbursable_amount
        currency = claim.amount.currency

        reimbursement_details = {
            "claim_id": claim_id,
            "employee_id": claim.employee_id,
            "employee_name": claim.employee_name,
            "total_reimbursement": total_reimbursement,
            "currency": currency,
            "reimbursement_date": date.today(),
            "payment_method": "Bank Transfer",
            "status": "Pending" if claim.status == ClaimStatus.APPROVED else "Not Approved",
        }

        self.log_success("Calculate Reimbursement")
        return reimbursement_details

    def calculate_variance(
        self,
        claim_id: ClaimId,
    ) -> dict:
        """
        Calculate variance between claimed and approved amounts.
        """
        self.log_start("Calculate Variance")

        claim = self._fetch_claim(claim_id)

        variance_results = []
        total_claimed = Decimal("0.00")
        total_approved = Decimal("0.00")

        for item in claim.expense_line_items:
            variance = item.claimed_amount - item.approved_amount
            variance_percent = (
                ((variance / item.claimed_amount) * 100) if item.claimed_amount > 0 else 0
            )

            variance_result = {
                "category": item.category_name,
                "claimed_amount": item.claimed_amount,
                "approved_amount": item.approved_amount,
                "variance_amount": variance,
                "variance_percent": round(variance_percent, 2),
                "reason": item.remarks if item.remarks else "No variance",
            }
            variance_results.append(variance_result)

            total_claimed += item.claimed_amount
            total_approved += item.approved_amount

        overall_variance = total_claimed - total_approved
        overall_variance_percent = (
            ((overall_variance / total_claimed) * 100) if total_claimed > 0 else 0
        )

        variance_summary = {
            "claim_id": claim_id,
            "total_claimed": total_claimed,
            "total_approved": total_approved,
            "overall_variance_amount": overall_variance,
            "overall_variance_percent": round(overall_variance_percent, 2),
            "item_variances": variance_results,
        }

        self.log_success("Calculate Variance")
        return variance_summary

    def get_claim_status(
        self,
        claim_id: ClaimId,
    ) -> dict:
        """
        Retrieve detailed status information for a claim.
        """
        self.log_start("Get Claim Status")

        claim = self._fetch_claim(claim_id)

        status_details = {
            "claim_id": claim_id,
            "status": claim.status,
            "submitted_at": claim.submitted_at,
            "employee_id": claim.employee_id,
            "employee_name": claim.employee_name,
            "total_amount": claim.amount.claimed_amount,
            "approved_amount": claim.amount.approved_amount,
            "reimbursable_amount": claim.amount.reimbursable_amount,
            "currency": claim.amount.currency,
        }

        if claim.approval:
            status_details["approval_date"] = claim.approval.approved_date
            status_details["approver_id"] = claim.approval.approver_id
            status_details["approver_name"] = claim.approval.approver_name
            status_details["approval_reason"] = claim.approval.reason

        self.log_success("Get Claim Status")
        return status_details

    def get_approval_status(
        self,
        claim_id: ClaimId,
    ) -> dict:
        """
        Retrieve approval status for a claim.
        """
        self.log_start("Get Approval Status")

        claim = self._fetch_claim(claim_id)

        approval_status = {
            "claim_id": claim_id,
            "status": claim.status,
            "approval_status": (
                "Not Required"
                if not claim.approval
                else "Approved" if claim.status == ClaimStatus.APPROVED else "Rejected"
            ),
            "submitted_t": str(claim.submitted_at),
        }

        if claim.approval:
            approval_status["approval_date"] = str(claim.approval.approved_date)
            approval_status["approver_id"] = claim.approval.approver_id
            approval_status["approver_name"] = claim.approval.approver_name
            approval_status["approval_reason"] = claim.approval.reason

        self.log_success("Get Approval Status")
        return approval_status

    def get_approval_history(
        self,
        employee_id: EmployeeId,
    ) -> list[dict]:
        """
        Retrieve approval history for an employee.
        """
        self.log_start("Get Approval History")

        # Get all claims for the employee
        employee_claims = self.list_employee_claims(employee_id)

        approval_history = []
        for claim in employee_claims:
            if claim.status in [ClaimStatus.APPROVED, ClaimStatus.REJECTED]:
                history_entry = {
                    "claim_id": claim.claim_id,
                    "trip_name": claim.trip_name,
                    "submitted_at": str(claim.submitted_at),
                    "status": claim.status,
                    "total_amount": str(claim.amount.claimed_amount),
                    "approved_amount": str(claim.amount.approved_amount),
                    "currency": claim.amount.currency,
                }

                if claim.approval:
                    history_entry["approval_date"] = str(claim.approval.approved_date)
                    history_entry["approver_name"] = claim.approval.approver_name
                    history_entry["approval_reason"] = claim.approval.reason

                approval_history.append(history_entry)

        self.log_success("Get Approval History")
        return approval_history

    ###########################################################################
    # Preview
    ###########################################################################

    def _build_preview(
        self,
        employee: Employee,
        line_items: list[ExpenseLineItem],
        request: SubmitExpenseClaimRequest,
    ) -> ClaimPreview:
        """
        Build a ClaimPreview DTO from calculated ExpenseLineItem value objects.

        Maps each domain ExpenseLineItem to an ExpenseItemResult output DTO,
        computes aggregate totals, and collects all applicable warnings.

        This is the only place where domain value objects (ExpenseLineItem)
        are translated into output DTOs (ExpenseItemResult).  The preview
        is never persisted.

        Args:
            employee:
                Validated employee entity.

            line_items:
                Calculated ExpenseLineItem value objects.

            request:
                The original submission request.

        Returns:
            ClaimPreview DTO for the caller.
        """
        total_requested = sum(
            (item.claimed_amount for item in line_items),
            start=Decimal("0.00"),
        )

        total_approved = sum(
            (item.approved_amount for item in line_items),
            start=Decimal("0.00"),
        )

        approval_required = any(item.approval_required for item in line_items)

        item_results = [
            ExpenseItemResult(
                category=item.category_name,
                requested_amount=item.claimed_amount,
                approved_amount=item.approved_amount,
                receipt_required=item.receipt_required,
                approval_required=item.approval_required,
                status=item.status,
                reason=item.remarks,
            )
            for item in line_items
        ]

        warnings = self._collect_warnings(line_items, request)

        return ClaimPreview(
            employee_id=str(employee.employee_id),
            employee_name=employee.full_name,
            employee_grade=employee.grade,
            total_requested=total_requested,
            total_approved=total_approved,
            approval_required=approval_required,
            items=item_results,
            warnings=warnings,
        )

    def _collect_warnings(
        self,
        line_items: list[ExpenseLineItem],
        request: SubmitExpenseClaimRequest,
    ) -> list[str]:
        """
        Collect human-readable warnings from calculated line items.

        Emits a warning for each item that was rejected, partially approved,
        requires receipt verification, or requires manager approval.

        Args:
            line_items:
                Calculated expense line items.
            request:
                The original submission request.

        Returns:
            Ordered list of warning strings.
        """
        warnings: list[str] = []

        for item, req_item in zip(line_items, request.expense_items, strict=True):
            if item.receipt_required and not req_item.receipt_available:
                warnings.append(
                    f"{item.category_name}: Receipt upload is pending and can be attached later."
                )

            if item.approval_required:
                warnings.append(f"{item.category_name}: Manager approval required.")

            if item.approved_amount < item.claimed_amount:
                if item.remarks:
                    warnings.append(f"{item.category_name}: {item.remarks}")
                else:
                    warnings.append(
                        f"{item.category_name}: Claimed amount exceeds policy daily limit."
                    )

        return warnings

    ###########################################################################
    # Persistence
    ###########################################################################

    def _persist_claim(
        self,
        claim: ExpenseClaim,
    ) -> None:
        """
        Persist the expense claim aggregate to the database.

        Delegates to the repository's upsert method, which creates the
        claim if it is new or replaces it if it already exists.

        Args:
            claim:
                The fully constructed ExpenseClaim aggregate.
        """
        item = claim.to_dynamodb_item()
        print("\n================ DYNAMODB ITEM ================\n")
        pprint(item)
        print("\n===============================================\n")

        self.claim_repository.save(claim)

    def _fetch_claim(
        self,
        claim_id: ClaimId,
    ) -> ExpenseClaim:
        """
        Retrieve a claim by identifier or raise if it does not exist.

        Args:
            claim_id:
                The claim identifier.

        Returns:
            ExpenseClaim aggregate.

        Raises:
            ServiceException: If no claim with the given ID is found.
        """
        claim = self.claim_repository.get_claim(claim_id)

        if claim is None:
            raise ServiceException(
                message=f"Expense claim '{claim_id}' does not exist.",
                error_code="CLAIM_NOT_FOUND",
            )

        return claim
