"""
Employee repository.

Provides employee-specific persistence operations.
"""

from __future__ import annotations

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config.settings import settings
from database.constants import EMAIL, EMAIL_INDEX, EMPLOYEE_ID
from exceptions.repository import RepositoryException
from models.employee import Employee
from repositories.base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    """
    Repository for Employee entities.
    """

    def __init__(self) -> None:

        super().__init__(
            table_name=settings.dynamodb.employees_table,
            partition_key=EMPLOYEE_ID,
            model_class=Employee,
        )

    ###########################################################################
    # Employee Queries
    ###########################################################################

    def get_by_employee_id(
        self,
        employee_id: str,
    ) -> Employee | None:
        """
        Retrieve an employee by employee ID.
        """

        return self.get(employee_id)

    def get_by_email(
        self,
        email: str,
    ) -> Employee | None:
        """
        Retrieve an employee using the email GSI.
        """

        try:
            employees = self.query(
                IndexName=EMAIL_INDEX,
                KeyConditionExpression=Key(EMAIL).eq(email),
                Limit=1,
            )

            if not employees:
                return None

            return employees[0]

        except ClientError as ex:
            raise RepositoryException(
                message=f"Unable to retrieve employee with email '{email}'.",
                cause=ex,
            ) from ex

    def employee_exists(
        self,
        employee_id: str,
    ) -> bool:
        """
        Check whether an employee exists.
        """

        return self.exists(employee_id)

    def list_active_employees(self) -> list[Employee]:
        """
        Return all active employees.
        """

        employees = self.scan()

        return [employee for employee in employees if employee.is_active]
