"""
Claim Amount Value Object.

Represents all financial information associated with an expense claim.

This is intentionally implemented as a Value Object rather than an Entity.
It has no identity and exists only as part of an ExpenseClaim aggregate.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import Field, computed_field, field_validator

from models.base import BaseSchema

DECIMAL_PRECISION = Decimal("0.01")


class ClaimAmount(BaseSchema):
    """
    Financial details of an expense claim.

    This object encapsulates all monetary values associated with
    reimbursement calculations.

    Attributes:
        claimed_amount:
            Original amount submitted by the employee.

        tax_amount:
            Tax included within the claimed amount.

        approved_amount:
            Amount approved after policy validation.

        reimbursable_amount:
            Final reimbursable amount paid by the company.

        employee_contribution:
            Amount to be paid by the employee.

        currency:
            ISO-4217 currency code.

        exchange_rate:
            Exchange rate against company base currency.
    """

    claimed_amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        description="Amount claimed by the employee.",
    )

    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
    )

    approved_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
    )

    reimbursable_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
    )

    employee_contribution: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
    )

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
    )

    exchange_rate: Decimal = Field(
        default=Decimal("1.0000"),
        gt=Decimal("0"),
    )

    @field_validator(
        "claimed_amount",
        "tax_amount",
        "approved_amount",
        "reimbursable_amount",
        "employee_contribution",
        mode="after",
    )
    @classmethod
    def normalize_decimal(cls, value: Decimal) -> Decimal:
        """
        Normalize monetary values to two decimal places.
        """
        return value.quantize(
            DECIMAL_PRECISION,
            rounding=ROUND_HALF_UP,
        )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        """
        Validate ISO currency format.
        """
        value = value.upper()

        if len(value) != 3:
            raise ValueError("Currency must be a valid ISO-4217 code.")

        return value

    @computed_field
    @property
    def company_contribution(self) -> Decimal:
        """
        Amount paid by the company.

        Returns:
            Approved reimbursement amount.
        """
        return self.reimbursable_amount

    @computed_field
    @property
    def total_cost(self) -> Decimal:
        """
        Total expense including tax.

        Returns:
            Total expense value.
        """
        return (self.claimed_amount + self.tax_amount).quantize(DECIMAL_PRECISION)

    @computed_field
    @property
    def non_reimbursable_amount(self) -> Decimal:
        """
        Amount not reimbursed.

        Returns:
            Difference between claimed and reimbursable amount.
        """
        return (self.claimed_amount - self.reimbursable_amount).quantize(DECIMAL_PRECISION)

    def approve(self, amount: Decimal) -> None:
        """
        Approve a reimbursement amount.

        Args:
            amount:
                Approved reimbursement.

        Raises:
            ValueError:
                If approved amount exceeds claimed amount.
        """
        if amount > self.claimed_amount:
            raise ValueError("Approved amount cannot exceed claimed amount.")

        amount = amount.quantize(
            DECIMAL_PRECISION,
            rounding=ROUND_HALF_UP,
        )

        self.approved_amount = amount
        self.reimbursable_amount = amount
        self.employee_contribution = (self.claimed_amount - amount).quantize(DECIMAL_PRECISION)

    def convert(self, exchange_rate: Decimal) -> Decimal:
        """
        Convert amount into company base currency.

        Args:
            exchange_rate:
                Exchange rate.

        Returns:
            Converted monetary value.
        """
        return (self.claimed_amount * exchange_rate).quantize(DECIMAL_PRECISION)
