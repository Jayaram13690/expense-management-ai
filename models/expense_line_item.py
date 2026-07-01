"""
Expense Line Item Value Object.

Represents a single calculated expense line within an ExpenseClaim aggregate.

This is a domain Value Object.  It has no identity outside the ExpenseClaim
aggregate and is always persisted as part of the claim document in DynamoDB.

It is NOT a DTO.

Design boundaries
-----------------
- DTOs (ExpenseItem, ExpenseItemResult) cross the service boundary.
- ExpenseLineItem lives inside the aggregate boundary.
- The service calculates an ExpenseLineItem from an ExpenseItem DTO and
  an ExpensePolicy, then attaches it to the ExpenseClaim aggregate.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from pydantic import Field, field_validator

from models.base import BaseSchema

DECIMAL_PRECISION = Decimal("0.01")


class LineItemStatus(StrEnum):
    """
    Processing status of a single expense line item.

    Determined during policy validation in the service layer and
    stored as part of the ExpenseClaim aggregate.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    REJECTED = "REJECTED"


class ExpenseLineItem(BaseSchema):
    """
    A single expense line within an expense claim aggregate.

    Represents one reimbursable expense (e.g. Hotel, Air Travel, Meals)
    that belongs to a larger business trip expense report.

    This value object is calculated by the service layer, embedded inside
    the ExpenseClaim aggregate root, and persisted as a nested DynamoDB
    document attribute.  It is never retrieved or persisted independently.

    Attributes:
        category_code:
            Short code identifying the expense category (e.g. HOTEL, AIR).

        category_name:
            Human-readable category name (e.g. Hotel Accommodation).

        expense_date:
            Date the expense was incurred.

        claimed_amount:
            Original amount submitted by the employee.

        approved_amount:
            Amount approved after policy validation.

        currency:
            ISO-4217 currency code for both claimed and approved amounts.

        receipt_required:
            Whether a receipt is mandatory per the applicable policy.

        approval_required:
            Whether manager approval is required per the applicable policy.

        status:
            Processing outcome of this line item after policy evaluation.

        remarks:
            Optional human-readable explanation for partial approval or
            rejection.  Populated when the status is not APPROVED.
    """

    category_code: str = Field(
        ...,
        min_length=2,
        max_length=20,
    )

    category_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    expense_date: date

    claimed_amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description="Amount claimed by the employee.",
    )

    approved_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        description="Amount approved after policy validation.",
    )

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
    )

    receipt_required: bool = True

    approval_required: bool = True

    status: LineItemStatus = LineItemStatus.PENDING

    remarks: str | None = Field(
        default=None,
        description="Explanation for partial approval or rejection.",
    )

    # --------------------------------------------------
    # Validators
    # --------------------------------------------------

    @field_validator("claimed_amount", "approved_amount", mode="after")
    @classmethod
    def normalize_decimal(cls, value: Decimal) -> Decimal:
        """Normalize monetary values to two decimal places."""
        return value.quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        """Validate and normalise the ISO-4217 currency code."""
        value = value.upper()

        if len(value) != 3:
            raise ValueError("Currency must be a valid ISO-4217 code.")

        return value

    # --------------------------------------------------
    # Domain Properties
    # --------------------------------------------------

    @property
    def is_approved(self) -> bool:
        """Whether this line item is fully approved."""
        return self.status == LineItemStatus.APPROVED

    @property
    def is_partially_approved(self) -> bool:
        """Whether this line item is partially approved."""
        return self.status == LineItemStatus.PARTIALLY_APPROVED

    @property
    def is_rejected(self) -> bool:
        """Whether this line item is rejected."""
        return self.status == LineItemStatus.REJECTED

    @property
    def reimbursable_amount(self) -> Decimal:
        """Amount to be reimbursed for this line item."""
        return self.approved_amount
