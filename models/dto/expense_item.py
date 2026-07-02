"""
Expense Item DTO.

Represents a single expense line submitted by an employee.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from models.base import BaseSchema


class ExpenseItem(BaseSchema):
    """
    One expense line item.
    """

    category_code: str = Field(
        ...,
        min_length=2,
        max_length=30,
    )

    description: str = Field(
        ...,
        min_length=3,
        max_length=500,
    )

    expense_date: date

    requested_amount: Decimal = Field(
        ...,
        gt=0,
    )

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
    )

    receipt_available: bool = False
