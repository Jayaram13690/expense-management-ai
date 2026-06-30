"""
Expense Category domain model.

Represents a reimbursable expense category within the
Enterprise AI Travel Expense Management System.
"""

from __future__ import annotations

from pydantic import Field

from common.identifiers import CategoryId
from models.base import BaseEntity


class ExpenseCategory(BaseEntity):
    """
    Expense category master entity.

    Represents a category of reimbursable expenses.
    """

    category_id: CategoryId

    category_code: str = Field(
        ...,
        min_length=2,
        max_length=20,
        pattern=r"^[A-Z0-9_]+$",
    )

    category_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    description: str = Field(
        ...,
        min_length=5,
        max_length=500,
    )

    reimbursement_required: bool = True

    receipt_required: bool = True

    approval_required: bool = True

    display_order: int = Field(
        default=1,
        ge=1,
    )

    @property
    def is_reimbursable(self) -> bool:
        """
        Whether this category is eligible for reimbursement.
        """

        return self.reimbursement_required

    @property
    def requires_receipt(self) -> bool:
        """
        Whether a receipt must be attached.
        """

        return self.receipt_required

    @property
    def requires_approval(self) -> bool:
        """
        Whether manager approval is required.
        """

        return self.approval_required
