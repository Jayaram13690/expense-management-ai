"""
Application enums.

This module contains strongly typed enumerations used throughout the
application to ensure type safety and avoid magic strings.

All string-valued enums inherit from StrEnum so that enum members compare
equal to their string values.  This is required because BaseSchema sets
use_enum_values=True, which causes Pydantic to store the raw string value
rather than the enum member.  Without StrEnum, comparisons such as
``self.status != ClaimStatus.DRAFT`` would always be True (str vs Enum).
"""

from enum import StrEnum


class Environment(StrEnum):
    """Application environment enumeration.

    Represents the different deployment environments for the application.
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ExpenseCategory(StrEnum):
    """Expense category enumeration.

    Represents the different categories of travel expenses that can be claimed.
    """

    AIRFARE = "airfare"
    ACCOMMODATION = "accommodation"
    MEALS = "meals"
    TRANSPORTATION = "transportation"
    ENTERTAINMENT = "entertainment"
    CONFERENCE = "conference"
    OFFICE_SUPPLIES = "office_supplies"
    COMMUNICATION = "communication"
    MISCELLANEOUS = "miscellaneous"


class ClaimStatus(StrEnum):
    """Claim status enumeration.

    Represents the different states a claim can be in during its lifecycle.
    """

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_VALIDATION = "under_validation"
    VALIDATED = "validated"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"
    CLOSED = "closed"


class ApprovalStatus(StrEnum):
    """Approval status enumeration.

    Represents the approval status of claims and individual expenses.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_MORE_INFO = "requires_more_info"


class ValidationStatus(StrEnum):
    """Validation status enumeration.

    Represents the validation status of expense claims and receipts.
    """

    NOT_VALIDATED = "not_validated"
    VALID = "valid"
    INVALID = "invalid"
    PENDING_REVIEW = "pending_review"
    FLAGGED = "flagged"


class LogLevel(StrEnum):
    """Log level enumeration.

    Represents the different severity levels for logging.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


__all__ = [
    "Environment",
    "ExpenseCategory",
    "ClaimStatus",
    "ApprovalStatus",
    "ValidationStatus",
    "LogLevel",
]
