"""
Employee domain model.

Represents an employee eligible to submit travel expense claims.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import EmailStr, Field, computed_field

from common.identifiers import EmployeeId
from models.base import BaseEntity


class EmploymentType(StrEnum):
    """Supported employment types."""

    FULL_TIME = "FULL_TIME"
    CONTRACTOR = "CONTRACTOR"
    INTERN = "INTERN"
    CONSULTANT = "CONSULTANT"


class Employee(BaseEntity):
    """
    Employee domain entity.

    Represents an employee within the organization.
    """

    employee_id: EmployeeId

    first_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    email: EmailStr

    department: str

    designation: str

    grade: str

    manager_id: str | None = None

    cost_center: str

    location: str

    employment_type: EmploymentType = EmploymentType.FULL_TIME

    preferred_currency: str = "USD"

    @computed_field
    @property
    def full_name(self) -> str:
        """Return employee full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_manager(self) -> bool:
        """Whether employee manages other employees."""
        return self.manager_id is None
