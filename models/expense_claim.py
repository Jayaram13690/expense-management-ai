"""
Expense Claim Aggregate Root.

This is the central business entity of the Enterprise AI Travel Expense
Management System.

All business operations revolve around this aggregate.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import Field

from common.identifiers import ClaimId, EmployeeId, PolicyId, TripId
from config.enums import ClaimStatus, ExpenseCategory
from models.approval import Approval
from models.base import BaseEntity
from models.claim_amount import ClaimAmount
from models.receipt import Receipt
from models.validation_result import ValidationResult


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(UTC)


class ExpenseClaim(BaseEntity):
    """
    Expense Claim Aggregate Root.

    Represents a travel expense claim submitted by an employee.
    """

    # claim_id: str = Field(
    #     ...,
    #     pattern=r"^CLM\d{4,12}$",
    # )

    claim_id: ClaimId

    employee_id: EmployeeId

    employee_name: str

    department: str

    trip_id: TripId | None = None

    business_purpose: str = Field(
        ...,
        min_length=5,
        max_length=500,
    )

    expense_category: ExpenseCategory

    expense_date: date

    submitted_at: datetime | None = None

    processed_at: datetime | None = None

    status: ClaimStatus = ClaimStatus.DRAFT

    amount: ClaimAmount

    approval: Approval = Field(default_factory=Approval)

    validation: ValidationResult = Field(default_factory=ValidationResult)

    receipts: list[Receipt] = Field(default_factory=list)

    policy_id: PolicyId | None = None

    notes: str | None = None

    # --------------------------------------------------
    # Business Behaviour
    # --------------------------------------------------

    def submit(self) -> None:
        """
        Submit the claim.
        """

        if self.status != ClaimStatus.DRAFT:
            raise ValueError("Only draft claims can be submitted.")

        self.status = ClaimStatus.SUBMITTED
        self.submitted_at = utc_now()

    def begin_validation(self) -> None:
        """
        Start validation workflow.
        """

        self.status = ClaimStatus.UNDER_VALIDATION

    def mark_validated(self) -> None:
        """
        Mark claim as validated.
        """

        self.status = ClaimStatus.VALIDATED

    def begin_review(self) -> None:
        """
        Send claim for review.
        """

        self.status = ClaimStatus.UNDER_REVIEW

    def approve(
        self,
        approver_id: str,
        approver_name: str,
    ) -> None:
        """
        Approve claim.
        """

        self.approval.approve(
            approver_id,
            approver_name,
        )

        self.status = ClaimStatus.APPROVED

    def reject(
        self,
        approver_id: str,
        approver_name: str,
        reason: str,
    ) -> None:
        """
        Reject claim.
        """

        self.approval.reject(
            approver_id,
            approver_name,
            reason,
        )

        self.status = ClaimStatus.REJECTED

    def reimburse(self) -> None:
        """
        Mark reimbursement completed.
        """

        if self.status != ClaimStatus.APPROVED:
            raise ValueError("Claim must be approved before reimbursement.")

        self.status = ClaimStatus.REIMBURSED

    def close(self) -> None:
        """
        Close claim.
        """

        self.status = ClaimStatus.CLOSED
        self.processed_at = utc_now()

    def add_receipt(
        self,
        receipt: Receipt,
    ) -> None:
        """
        Attach receipt.

        Args:
            receipt:
                Receipt entity.
        """

        self.receipts.append(receipt)

    @property
    def total_receipts(self) -> int:
        """
        Number of attached receipts.
        """

        return len(self.receipts)

    @property
    def total_claim_amount(self) -> Decimal:
        """
        Claimed amount.
        """

        return self.amount.claimed_amount

    @property
    def reimbursable_amount(self) -> Decimal:
        """
        Approved reimbursement.
        """

        return self.amount.reimbursable_amount

    @property
    def requires_manual_review(self) -> bool:
        """
        Determine whether manual review is required.
        """

        return self.validation.requires_manual_review
