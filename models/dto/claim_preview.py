"""
Claim Preview DTO.

Returned after reimbursement calculation.
Nothing is persisted.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from models.base import BaseSchema


class ExpenseItemResult(BaseSchema):
    """
    Calculated result for one expense item.
    """

    category: str

    requested_amount: Decimal

    approved_amount: Decimal

    receipt_required: bool

    approval_required: bool

    status: str

    reason: str | None = None


class ClaimPreview(BaseSchema):
    """
    Claim preview returned before submission.
    """

    employee_id: str

    employee_name: str

    employee_grade: str

    total_requested: Decimal

    total_approved: Decimal

    approval_required: bool

    items: list[ExpenseItemResult] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )