"""
Allowance Validation Result Model.

Reusable structured result produced by ExpenseAllowanceService.

This model is the single canonical representation of a per-category
monthly allowance check.  Every component that needs allowance information
— agents, tools, future APIs, dashboards, and evaluators — consumes this
model instead of raw booleans.

Design
------
- Immutable value object: constructed once, read many times.
- Currency-agnostic: stores amounts as Decimal; currency carried separately.
- Business-friendly: includes a human-readable validation_message.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import Field, model_validator

from models.base import BaseSchema

_TWO_PLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to two decimal places."""
    return value.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


class AllowanceValidationResult(BaseSchema):
    """
    Per-category monthly allowance validation result.

    Produced by ExpenseAllowanceService.validate_claim_allowance() and
    ExpenseAllowanceService.get_category_allowance().

    Attributes
    ----------
    category_code:
        Short code identifying the expense category (e.g. HOTEL, MEALS).

    category_name:
        Human-readable category name (e.g. Hotel Accommodation, Meals).

    monthly_limit:
        Maximum amount allowed per calendar month per the applicable policy.

    already_consumed:
        Sum of approved_amount values from APPROVED claims in the current
        calendar month for this employee and category.

    remaining:
        Monthly limit minus already consumed.  Always >= 0.

    requested_amount:
        Amount the employee is attempting to claim in the current submission.

    exceeded:
        True when requested_amount > remaining.

    exceeded_by:
        Amount by which the requested exceeds the remaining.  Zero when not
        exceeded.

    currency:
        ISO-4217 currency code (default INR).

    validation_message:
        Business-friendly human-readable description of the result.
    """

    category_code: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Expense category code.",
    )

    category_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Human-readable category name.",
    )

    monthly_limit: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Monthly policy limit for this category.",
    )

    already_consumed: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Amount already consumed from APPROVED claims this month.",
    )

    remaining: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Remaining allowance (monthly_limit - already_consumed). Never negative.",
    )

    requested_amount: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Amount requested in the current claim.",
    )

    exceeded: bool = Field(
        ...,
        description="True when requested_amount > remaining.",
    )

    exceeded_by: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        description="Amount by which the requested exceeds the remaining.",
    )

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
        description="ISO-4217 currency code.",
    )

    validation_message: str = Field(
        ...,
        min_length=1,
        description="Business-friendly validation message.",
    )

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _normalize_decimals(self) -> "AllowanceValidationResult":
        """Normalize all Decimal fields to two decimal places."""
        object.__setattr__(self, "monthly_limit", _q(self.monthly_limit))
        object.__setattr__(self, "already_consumed", _q(self.already_consumed))
        object.__setattr__(self, "remaining", _q(self.remaining))
        object.__setattr__(self, "requested_amount", _q(self.requested_amount))
        object.__setattr__(self, "exceeded_by", _q(self.exceeded_by))
        return self

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        category_code: str,
        category_name: str,
        monthly_limit: Decimal,
        already_consumed: Decimal,
        requested_amount: Decimal,
        currency: str = "INR",
    ) -> "AllowanceValidationResult":
        """
        Construct an AllowanceValidationResult with derived fields.

        The ``remaining``, ``exceeded``, ``exceeded_by``, and
        ``validation_message`` fields are computed automatically from the
        supplied inputs so callers never need to compute them manually.

        Parameters
        ----------
        category_code:
            Expense category code.
        category_name:
            Human-readable category name.
        monthly_limit:
            Policy monthly limit for this category and employee grade.
        already_consumed:
            Sum of approved amounts from APPROVED claims this month.
        requested_amount:
            Amount the employee wishes to claim in the current submission.
        currency:
            ISO-4217 currency code (default INR).
        """
        # Remaining can never be negative
        remaining = max(Decimal("0.00"), monthly_limit - already_consumed)
        exceeded = requested_amount > remaining
        exceeded_by = (
            max(Decimal("0.00"), requested_amount - remaining) if exceeded else Decimal("0.00")
        )

        if exceeded:
            validation_message = (
                f"{category_name} monthly allowance exceeded.\n"
                f"Monthly Limit    : {currency} {_q(monthly_limit):,}\n"
                f"Already Consumed : {currency} {_q(already_consumed):,}\n"
                f"Remaining        : {currency} {_q(remaining):,}\n"
                f"Current Claim    : {currency} {_q(requested_amount):,}\n"
                f"Exceeded By      : {currency} {_q(exceeded_by):,}\n"
                f"Please modify your expenses before submitting."
            )
        else:
            validation_message = (
                f"{category_name} allowance is within the monthly limit.\n"
                f"Monthly Limit    : {currency} {_q(monthly_limit):,}\n"
                f"Already Consumed : {currency} {_q(already_consumed):,}\n"
                f"Remaining        : {currency} {_q(remaining):,}\n"
                f"Current Claim    : {currency} {_q(requested_amount):,}"
            )

        return cls(
            category_code=category_code,
            category_name=category_name,
            monthly_limit=monthly_limit,
            already_consumed=already_consumed,
            remaining=remaining,
            requested_amount=requested_amount,
            exceeded=exceeded,
            exceeded_by=exceeded_by,
            currency=currency,
            validation_message=validation_message,
        )

    # ------------------------------------------------------------------
    # Domain properties
    # ------------------------------------------------------------------

    @property
    def is_valid(self) -> bool:
        """True when the requested amount does not exceed remaining allowance."""
        return not self.exceeded

    def summary_dict(self) -> dict:
        """Return a plain dict suitable for API responses and logging."""
        return {
            "category_code": self.category_code,
            "category_name": self.category_name,
            "monthly_limit": str(self.monthly_limit),
            "already_consumed": str(self.already_consumed),
            "remaining": str(self.remaining),
            "requested_amount": str(self.requested_amount),
            "exceeded": self.exceeded,
            "exceeded_by": str(self.exceeded_by),
            "currency": self.currency,
            "validation_message": self.validation_message,
        }


__all__ = ["AllowanceValidationResult"]
