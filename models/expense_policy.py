"""
Expense policy domain model.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from common.identifiers import CategoryId, PolicyId
from models.base import BaseEntity


class ExpensePolicy(BaseEntity):
    """
    Expense reimbursement policy.
    """

    policy_id: PolicyId

    employee_grade: str

    category_id: CategoryId

    daily_limit: Decimal = Field(
        ...,
        gt=0,
    )

    monthly_limit: Decimal = Field(
        ...,
        gt=0,
    )

    receipt_required: bool = True

    approval_required: bool = True

    currency: str = "USD"

    reimbursement_percentage: Decimal = Decimal("100.00")

    processing_time_days: int = 7

    special_conditions: str | None = None

    effective_from: date

    effective_to: date

    description: str | None = None

    def is_effective(self, current_date: date) -> bool:
        """
        Check whether policy is active.
        """
        return self.effective_from <= current_date <= self.effective_to

    def is_amount_allowed(self, amount: Decimal) -> bool:
        """
        Validate reimbursement amount.
        """
        return amount <= self.daily_limit
