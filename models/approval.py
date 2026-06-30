"""
Approval Value Object.

Represents the approval state of an expense claim.

This is a Value Object and forms part of the ExpenseClaim aggregate.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, field_validator

from config.enums import ApprovalStatus
from models.base import BaseSchema


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


class Approval(BaseSchema):
    """
    Approval information for an expense claim.

    This object encapsulates the approval lifecycle.
    """

    status: ApprovalStatus = ApprovalStatus.PENDING

    approver_id: str | None = Field(
        default=None,
        description="Employee ID of the approver.",
    )

    approver_name: str | None = None

    approved_at: datetime | None = None

    rejection_reason: str | None = None

    comments: str | None = None

    approval_level: int = Field(
        default=1,
        ge=1,
        description="Current approval level.",
    )

    auto_approved: bool = False

    ai_recommended: bool = False

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Validate rejection reason length.
        """
        if value is not None:
            value = value.strip()

            if len(value) < 5:
                raise ValueError("Rejection reason must contain at least 5 characters.")

        return value

    def approve(
        self,
        approver_id: str,
        approver_name: str,
        comments: str | None = None,
    ) -> None:
        """
        Approve the claim.

        Args:
            approver_id:
                Employee ID of approver.

            approver_name:
                Name of approver.

            comments:
                Optional approval comments.
        """

        self.status = ApprovalStatus.APPROVED
        self.approver_id = approver_id
        self.approver_name = approver_name
        self.comments = comments
        self.approved_at = utc_now()

    def reject(
        self,
        approver_id: str,
        approver_name: str,
        reason: str,
    ) -> None:
        """
        Reject the claim.

        Args:
            approver_id:
                Employee ID.

            approver_name:
                Name.

            reason:
                Rejection reason.
        """

        self.status = ApprovalStatus.REJECTED
        self.approver_id = approver_id
        self.approver_name = approver_name
        self.rejection_reason = reason
        self.approved_at = utc_now()

    def mark_auto_approved(self) -> None:
        """
        Mark claim as automatically approved.
        """

        self.status = ApprovalStatus.APPROVED
        self.auto_approved = True
        self.approved_at = utc_now()

    def mark_ai_recommended(self) -> None:
        """
        Mark that AI recommends approval.

        Human approval is still required.
        """

        self.ai_recommended = True

    @property
    def is_pending(self) -> bool:
        """Whether approval is pending."""
        return self.status == ApprovalStatus.PENDING

    @property
    def is_approved(self) -> bool:
        """Whether claim is approved."""
        return self.status == ApprovalStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        """Whether claim is rejected."""
        return self.status == ApprovalStatus.REJECTED
