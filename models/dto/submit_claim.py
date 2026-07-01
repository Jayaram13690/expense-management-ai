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

    Attributes:
        employee_id:
            Identifier of the submitting employee.

        trip_name:
            Short, descriptive label for the business trip.
            Example: "AWS Summit Bangalore 2026"

        business_purpose:
            Justification for the trip in business terms.
            Example: "Attend AWS Summit to evaluate Amazon Bedrock AgentCore
            and AI solutions for the engineering roadmap."

        destination:
            Primary destination of the trip.

        trip_start_date:
            First date of the trip.

        trip_end_date:
            Last date of the trip.

        expense_items:
            Individual expense line items incurred during the trip.

        comments:
            Free-form notes from the employee.
    """

    employee_id: EmployeeId

    trip_name: str = Field(
        ...,
        min_length=3,
        max_length=200,
    )

    business_purpose: str = Field(
        ...,
        min_length=10,
        max_length=500,
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
