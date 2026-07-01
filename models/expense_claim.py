"""
Expense Claim Aggregate Root.

This is the central business entity of the Enterprise AI Travel Expense
Management System.

All business operations revolve around this aggregate.

Design
------
One ExpenseClaim represents one complete business trip expense report.
Each trip contains multiple expense line items (Hotel, Air, Meals, Taxi, etc.).

The aggregate enforces all consistency rules and lifecycle transitions
internally.  The service orchestrates — the aggregate decides.

Aggregate invariants (enforced here, not in the service layer):
    - A claim with no line items cannot be submitted.
    - Only a DRAFT claim can be submitted.
    - Only a SUBMITTED or UNDER_REVIEW claim can be approved or rejected.
    - Only an APPROVED claim can be reimbursed.
    - trip_end_date must not precede trip_start_date.

Aggregate boundaries
--------------------
- ExpenseClaim          Aggregate Root  (this file)
- ExpenseLineItem       Value Object    (models/expense_line_item.py)
- ClaimAmount           Value Object    (models/claim_amount.py)
- Approval              Value Object    (models/approval.py)
- ValidationResult      Value Object    (models/validation_result.py)
- Receipt               Entity          (models/receipt.py)
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from common.identifiers import ClaimId, EmployeeId, PolicyId, TripId
from config.enums import ClaimStatus
from models.approval import Approval
from models.base import BaseEntity
from models.claim_amount import ClaimAmount
from models.expense_line_item import ExpenseLineItem
from models.receipt import Receipt
from models.validation_result import ValidationResult


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(UTC)


class ExpenseClaim(BaseEntity):
    """
    Expense Claim Aggregate Root.

    Represents a complete travel expense report submitted by an employee.
    One claim covers one business trip and contains multiple expense line
    items, each validated independently against the applicable policy.

    Attributes:
        claim_id:
            Unique business identifier for this claim.

        employee_id:
            Identifier of the employee submitting the claim.

        employee_name:
            Full name of the employee at the time of submission.

        employee_grade:
            Grade of the employee, used to determine applicable policies.

        department:
            Department of the employee.

        trip_id:
            Optional identifier linking this claim to a pre-approved trip.

        trip_name:
            Short descriptive label for the business trip.

        business_purpose:
            Business justification for the trip.

        destination:
            Primary destination of the business trip.

        trip_start_date:
            First date of the business trip.

        trip_end_date:
            Last date of the business trip.  Must not precede trip_start_date.

        submitted_at:
            Timestamp when the claim was submitted.

        processed_at:
            Timestamp when the claim was fully processed (approved/rejected).

        status:
            Current lifecycle status of the claim.

        amount:
            Aggregate-level financial summary (claimed, approved, reimbursable).

        approval:
            Approval state including approver identity and timestamp.

        validation:
            Validation result including policy violations and fraud score.

        receipts:
            Receipts attached to this claim.

        expense_line_items:
            Individual expense line items that make up this claim.

        policy_id:
            Optional policy override applied at the claim level.

        notes:
            Free-form notes from the employee.
    """

    claim_id: ClaimId

    employee_id: EmployeeId

    employee_name: str

    employee_grade: str

    department: str

    trip_id: TripId | None = None

    trip_name: str = Field(
        ...,
        min_length=3,
        max_length=200,
    )

    business_purpose: str = Field(
        ...,
        min_length=10,
        max_length=500,
    )

    destination: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    trip_start_date: date

    trip_end_date: date

    submitted_at: datetime | None = None

    processed_at: datetime | None = None

    status: ClaimStatus = ClaimStatus.DRAFT

    amount: ClaimAmount

    approval: Approval = Field(default_factory=Approval)

    validation: ValidationResult = Field(default_factory=ValidationResult)

    receipts: list[Receipt] = Field(default_factory=list)

    expense_line_items: list[ExpenseLineItem] = Field(default_factory=list)

    policy_id: PolicyId | None = None

    notes: str | None = None

    # --------------------------------------------------
    # Aggregate Invariants — Construction
    # --------------------------------------------------

    @model_validator(mode="after")
    def validate_trip_dates(self) -> ExpenseClaim:
        """
        Enforce that trip_end_date is not before trip_start_date.

        Raises:
            ValueError: If trip_end_date precedes trip_start_date.
        """
        if self.trip_end_date < self.trip_start_date:
            raise ValueError(
                f"trip_end_date '{self.trip_end_date}' cannot be before "
                f"trip_start_date '{self.trip_start_date}'."
            )

        return self

    # --------------------------------------------------
    # Computed Properties — Line Item Aggregations
    # --------------------------------------------------

    @property
    def total_requested(self) -> Decimal:
        """Sum of all claimed amounts across expense line items."""
        return sum(
            (item.claimed_amount for item in self.expense_line_items),
            start=Decimal("0.00"),
        )

    @property
    def total_approved(self) -> Decimal:
        """Sum of all approved amounts across expense line items."""
        return sum(
            (item.approved_amount for item in self.expense_line_items),
            start=Decimal("0.00"),
        )

    @property
    def total_items(self) -> int:
        """Total number of expense line items."""
        return len(self.expense_line_items)

    @property
    def approved_items(self) -> int:
        """Number of fully approved line items."""
        return sum(1 for item in self.expense_line_items if item.is_approved)

    @property
    def partially_approved_items(self) -> int:
        """Number of partially approved line items."""
        return sum(1 for item in self.expense_line_items if item.is_partially_approved)

    @property
    def rejected_items(self) -> int:
        """Number of rejected line items."""
        return sum(1 for item in self.expense_line_items if item.is_rejected)

    @property
    def approval_required(self) -> bool:
        """Whether any line item requires manager approval per policy."""
        return any(item.approval_required for item in self.expense_line_items)

    # --------------------------------------------------
    # Existing Computed Properties (preserved)
    # --------------------------------------------------

    @property
    def total_receipts(self) -> int:
        """Number of attached receipts."""
        return len(self.receipts)

    @property
    def total_claim_amount(self) -> Decimal:
        """Total claimed amount from the aggregate-level ClaimAmount summary."""
        return self.amount.claimed_amount

    @property
    def reimbursable_amount(self) -> Decimal:
        """Approved reimbursement from the aggregate-level ClaimAmount summary."""
        return self.amount.reimbursable_amount

    @property
    def requires_manual_review(self) -> bool:
        """Determine whether manual review is required."""
        return self.validation.requires_manual_review

    # --------------------------------------------------
    # Business Behaviour — Line Items
    # --------------------------------------------------

    def add_line_item(
        self,
        item: ExpenseLineItem,
    ) -> None:
        """
        Add a validated expense line item.

        Line items can only be added while the claim is in DRAFT status.

        Raises:
            ValueError:
                If the claim has already been submitted.
        """
        if self.status != ClaimStatus.DRAFT:
            raise ValueError(
                "Expense line items cannot be modified after the claim has been submitted."
            )

        self.expense_line_items.append(item)

    # --------------------------------------------------
    # Business Behaviour — Claim Lifecycle
    # --------------------------------------------------

    def to_dynamodb_item(self) -> dict:
        """
        Convert the aggregate into the DynamoDB storage format.

        Adds the attributes required by the GSIs while keeping the
        domain model independent of DynamoDB naming.
        """

        item = super().to_dynamodb_item()

        # ---------------------------------------------------------
        # Required GSI attributes
        # ---------------------------------------------------------

        item["claim_status"] = self.status

        if self.submitted_at is not None:
            item["submission_date"] = self.submitted_at.isoformat()

        if self.approval.approver_id:
            item["approver_id"] = self.approval.approver_id

        return item

    @classmethod
    def from_dict(cls, data: dict) -> ExpenseClaim:
        """
        Convert a DynamoDB item into an ExpenseClaim domain object.
        """
        item = dict(data)

        # Remove persistence-only fields
        item.pop("claim_status", None)
        item.pop("submission_date", None)
        item.pop("approver_id", None)

        return cls.model_validate(item)

    def submit(self) -> None:
        """
        Submit the claim for manager review.

        Aggregate invariants checked here:
            - The claim must be in DRAFT status.
            - The claim must contain at least one expense line item.

        Raises:
            ValueError: If any invariant is violated.
        """
        if self.status != ClaimStatus.DRAFT:
            raise ValueError(
                f"Only DRAFT claims can be submitted. Current status: '{self.status}'."
            )

        if not self.expense_line_items:
            raise ValueError(
                "A claim must contain at least one expense line item before it can be submitted."
            )

        self.status = ClaimStatus.SUBMITTED
        self.submitted_at = utc_now()

    def begin_validation(self) -> None:
        """Transition claim to the validation stage."""
        self.status = ClaimStatus.UNDER_VALIDATION

    def mark_validated(self) -> None:
        """Mark the claim as validated."""
        self.status = ClaimStatus.VALIDATED

    def begin_review(self) -> None:
        """Transition claim to manual review."""
        self.status = ClaimStatus.UNDER_REVIEW

    def finalize_approval(
        self,
        approver_id: str,
        approver_name: str,
    ) -> None:
        """
        Approve the claim and update all financial state.

        This is the single point of approval for the aggregate.  It
        internally updates the Approval value object, finalises the
        ClaimAmount reimbursable total, and transitions to APPROVED status.

        The service must not manipulate ``claim.approval`` or
        ``claim.amount`` directly — it calls this method instead.

        Aggregate invariants checked here:
            - The claim must be in SUBMITTED or UNDER_REVIEW status.

        Args:
            approver_id:
                Employee ID of the approving manager.

            approver_name:
                Full name of the approving manager.

        Raises:
            ValueError: If the claim is not in an approvable status.
        """
        if self.status not in (
            ClaimStatus.SUBMITTED,
            ClaimStatus.UNDER_REVIEW,
        ):
            raise ValueError(
                f"Only SUBMITTED or UNDER_REVIEW claims can be approved. "
                f"Current status: '{self.status}'."
            )

        self.approval.approve(approver_id, approver_name)
        self.amount.approve(self.total_approved)
        self.status = ClaimStatus.APPROVED
        self.processed_at = utc_now()

    def finalize_rejection(
        self,
        approver_id: str,
        approver_name: str,
        reason: str,
    ) -> None:
        """
        Reject the claim and record the manager's decision.

        This is the single point of rejection for the aggregate.  It
        internally updates the Approval value object and transitions
        to REJECTED status.

        The service must not manipulate ``claim.approval`` directly —
        it calls this method instead.

        Aggregate invariants checked here:
            - The claim must be in SUBMITTED or UNDER_REVIEW status.

        Args:
            approver_id:
                Employee ID of the rejecting manager.

            approver_name:
                Full name of the rejecting manager.

            reason:
                Reason for rejection, communicated back to the employee.

        Raises:
            ValueError: If the claim is not in a rejectable status.
        """
        if self.status not in (
            ClaimStatus.SUBMITTED,
            ClaimStatus.UNDER_REVIEW,
        ):
            raise ValueError(
                f"Only SUBMITTED or UNDER_REVIEW claims can be rejected. "
                f"Current status: '{self.status}'."
            )

        self.approval.reject(approver_id, approver_name, reason)
        self.status = ClaimStatus.REJECTED
        self.processed_at = utc_now()

    def reimburse(self) -> None:
        """
        Mark reimbursement as completed.

        Aggregate invariants checked here:
            - The claim must be APPROVED before it can be reimbursed.

        Raises:
            ValueError: If the claim is not approved.
        """
        if self.status != ClaimStatus.APPROVED:
            raise ValueError(
                f"Only APPROVED claims can be reimbursed. Current status: '{self.status}'."
            )

        self.status = ClaimStatus.REIMBURSED

    def close(self) -> None:
        """
        Close the claim and record the processing timestamp.

        A claim can be closed from REIMBURSED or REJECTED status,
        representing the final terminal state.

        Raises:
            ValueError: If the claim is not in a closeable status.
        """
        if self.status not in (
            ClaimStatus.REIMBURSED,
            ClaimStatus.REJECTED,
        ):
            raise ValueError(
                f"Only REIMBURSED or REJECTED claims can be closed. "
                f"Current status: '{self.status}'."
            )

        self.status = ClaimStatus.CLOSED
        self.processed_at = utc_now()

    def add_receipt(
        self,
        receipt: Receipt,
    ) -> None:
        """
        Attach a receipt.
        Prevent duplicate receipts from being attached.
        """
        if any(existing.receipt_id == receipt.receipt_id for existing in self.receipts):
            raise ValueError(f"Receipt '{receipt.receipt_id}' is already attached to this claim.")

        self.receipts.append(receipt)
