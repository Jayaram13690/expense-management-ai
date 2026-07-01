"""
Validation Result Value Object.

Represents the outcome of policy validation and AI validation
for an expense claim.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import Field, field_validator

from config.enums import ValidationStatus
from models.base import BaseSchema


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(UTC)


class ValidationResult(BaseSchema):
    """
    Validation result for an expense claim.

    This value object stores the outcome of business rule validation,
    policy validation, and future AI validation.
    """

    status: ValidationStatus = ValidationStatus.PENDING_REVIEW

    confidence_score: Decimal = Field(
        default=Decimal("1.00"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="AI confidence score.",
    )

    fraud_score: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="AI fraud probability.",
    )

    missing_receipts: list[str] = Field(default_factory=list)

    policy_violations: list[str] = Field(default_factory=list)

    validation_errors: list[str] = Field(default_factory=list)

    validation_warnings: list[str] = Field(default_factory=list)

    validated_at: datetime | None = None

    validated_by: str | None = None

    @field_validator("validation_errors", "validation_warnings")
    @classmethod
    def remove_empty_messages(cls, values: list[str]) -> list[str]:
        """Remove blank validation messages."""
        return [message.strip() for message in values if message.strip()]

    def mark_valid(self, validator: str = "system") -> None:
        """
        Mark validation as successful.

        Args:
            validator:
                Name of validator or agent.
        """
        self.status = ValidationStatus.VALID
        self.validated_at = utc_now()
        self.validated_by = validator

    def mark_invalid(self, validator: str = "system") -> None:
        """
        Mark validation as failed.

        Args:
            validator:
                Name of validator or agent.
        """
        self.status = ValidationStatus.INVALID
        self.validated_at = utc_now()
        self.validated_by = validator

    def add_error(self, message: str) -> None:
        """
        Add validation error.
        """
        if message not in self.validation_errors:
            self.validation_errors.append(message)

    def add_warning(self, message: str) -> None:
        """
        Add validation warning.
        """
        if message not in self.validation_warnings:
            self.validation_warnings.append(message)

    def add_policy_violation(self, violation: str) -> None:
        """
        Add policy violation.
        """
        if violation not in self.policy_violations:
            self.policy_violations.append(violation)

    def add_missing_receipt(self, receipt_name: str) -> None:
        """
        Register a missing receipt.
        """
        if receipt_name not in self.missing_receipts:
            self.missing_receipts.append(receipt_name)

    @property
    def has_errors(self) -> bool:
        """Whether validation contains errors."""
        return bool(self.validation_errors)

    @property
    def has_warnings(self) -> bool:
        """Whether validation contains warnings."""
        return bool(self.validation_warnings)

    @property
    def has_policy_violations(self) -> bool:
        """Whether policy violations exist."""
        return bool(self.policy_violations)

    @property
    def requires_manual_review(self) -> bool:
        """
        Determine whether manual review is required.

        Manual review is required if:

        - Fraud score >= 0.70
        - Policy violations exist
        - Validation errors exist
        """

        return self.fraud_score >= 0.70 or self.has_policy_violations or self.has_errors
