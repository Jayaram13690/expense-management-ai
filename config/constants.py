"""
Application constants.

This module contains application-wide constants that are used across
multiple components. These values are not expected to change during
runtime and provide a single source of truth for common configurations.

Note: Configurable values have been moved to settings.py. This file
contains only immutable constants that should not be changed through
configuration.
"""

# Date and time formats
DATE_FORMAT: str = "%Y-%m-%d"
DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"
ISO_8601_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"

# File and storage constants
SUPPORTED_FILE_EXTENSIONS: tuple = (".pdf", ".jpg", ".jpeg", ".png", ".gif")
MAX_RECEIPT_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB
MAX_RECEIPT_SIZE_MB: int = 5

# Currency and financial constants
DEFAULT_CURRENCY: str = "USD"
SUPPORTED_CURRENCIES: tuple = ("USD", "EUR", "GBP", "JPY", "CAD", "AUD")
MAX_EXPENSE_AMOUNT: float = 10000.0

# Pagination constants
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# Validation and processing constants
MAX_CONCURRENT_PROCESSING: int = 10
BATCH_PROCESSING_SIZE: int = 50

# Cache constants
CACHE_TTL_SECONDS: int = 3600  # 1 hour
SHORT_CACHE_TTL_SECONDS: int = 300  # 5 minutes

# Regular expressions
EMAIL_REGEX: str = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
EXPENSE_AMOUNT_REGEX: str = r"^\d+\.?\d{0,2}$"

# Security constants
MAX_PASSWORD_LENGTH: int = 128
MIN_PASSWORD_LENGTH: int = 8
TOKEN_EXPIRATION_HOURS: int = 24

# Business rules constants
MAX_CLAIM_AGE_DAYS: int = 90  # Claims older than 90 days cannot be submitted
MIN_RECEIPT_COUNT: int = 1
MAX_RECEIPT_COUNT: int = 10

# Notification constants
NOTIFICATION_RETRY_LIMIT: int = 3
NOTIFICATION_EXPIRATION_DAYS: int = 7

# Audit and compliance constants
AUDIT_LOG_RETENTION_DAYS: int = 365
COMPLIANCE_CHECK_INTERVAL_HOURS: int = 24

__all__ = [
    "DATE_FORMAT",
    "DATETIME_FORMAT",
    "TIMESTAMP_FORMAT",
    "ISO_8601_FORMAT",
    "SUPPORTED_FILE_EXTENSIONS",
    "MAX_RECEIPT_SIZE_BYTES",
    "MAX_RECEIPT_SIZE_MB",
    "DEFAULT_CURRENCY",
    "SUPPORTED_CURRENCIES",
    "MAX_EXPENSE_AMOUNT",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "MAX_CONCURRENT_PROCESSING",
    "BATCH_PROCESSING_SIZE",
    "CACHE_TTL_SECONDS",
    "SHORT_CACHE_TTL_SECONDS",
    "EMAIL_REGEX",
    "EXPENSE_AMOUNT_REGEX",
    "MAX_PASSWORD_LENGTH",
    "MIN_PASSWORD_LENGTH",
    "TOKEN_EXPIRATION_HOURS",
    "MAX_CLAIM_AGE_DAYS",
    "MIN_RECEIPT_COUNT",
    "MAX_RECEIPT_COUNT",
    "NOTIFICATION_RETRY_LIMIT",
    "NOTIFICATION_EXPIRATION_DAYS",
    "AUDIT_LOG_RETENTION_DAYS",
    "COMPLIANCE_CHECK_INTERVAL_HOURS",
]
