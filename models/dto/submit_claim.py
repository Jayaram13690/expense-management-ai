"""
Submit Claim Request DTO.
"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from common.identifiers import EmployeeId
from models.base import BaseSchema
from models.dto.expense_item import ExpenseItem


class SubmitExpenseClaimRequest(BaseSchema):
    """
    Request used to submit an expense claim.
    """

    employee_id: EmployeeId

    trip_name: str = Field(
        ...,
        min_length=3,
        max_length=200,
    )

    destination: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    trip_start_date: date

    trip_end_date: date

    expense_items: list[ExpenseItem] = Field(
        min_length=1,
    )

    comments: str | None = None