"""
Base exception hierarchy for the Enterprise AI Travel Expense Management System.

Every custom application exception must inherit from ApplicationException.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from utils.context import (
    get_request_id,
    get_workflow_id,
)


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(UTC)


class ApplicationException(Exception):
    """
    Base application exception.

    All custom exceptions inherit from this class.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        recoverable: bool = False,
        metadata: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)

        self.message = message

        self.error_code = error_code

        self.recoverable = recoverable

        self.metadata = metadata or {}

        self.cause = cause

        self.timestamp = utc_now()

        self.workflow_id = get_workflow_id()

        self.request_id = get_request_id()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception into serializable dictionary.
        """

        return {
            "error_code": self.error_code,
            "message": self.message,
            "recoverable": self.recoverable,
            "metadata": self.metadata,
            "workflow_id": self.workflow_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        """
        Human-readable exception.
        """

        return f"[{self.error_code}] {self.message}"
