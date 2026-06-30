"""
Employee service.

Contains business operations related to employees.
"""

from __future__ import annotations

from common.identifiers import EmployeeId
from exceptions.repository import RepositoryException
from models.employee import Employee
from repositories.employee_repository import EmployeeRepository
from services.base import BaseService


class EmployeeService(BaseService):
    """
    Employee business service.
    """

    def __init__(self) -> None:
        super().__init__()

        self.employee_repository = EmployeeRepository()

    ###########################################################################
    # Employee Operations
    ###########################################################################

    def get_employee(
        self,
        employee_id: EmployeeId,
    ) -> Employee:
        """
        Retrieve an employee.

        Raises:
            RepositoryException:
                If the employee does not exist.
        """

        self.log_start("Get Employee")

        employee = self.employee_repository.get_by_employee_id(
            employee_id
        )

        if employee is None:
            self.log_failure(
                "Get Employee",
                f"Employee '{employee_id}' does not exist.",
            )

            raise RepositoryException(
                message=f"Employee '{employee_id}' does not exist."
            )

        self.log_success("Get Employee")

        return employee

    def get_employee_by_email(
        self,
        email: str,
    ) -> Employee:
        """
        Retrieve an employee using email.
        """

        self.log_start("Get Employee By Email")

        employee = self.employee_repository.get_by_email(email)

        if employee is None:

            self.log_failure(
                "Get Employee By Email",
                f"Employee with email '{email}' does not exist.",
            )

            raise RepositoryException(
                message=f"Employee with email '{email}' does not exist."
            )

        self.log_success("Get Employee By Email")

        return employee

    def employee_exists(
        self,
        employee_id: EmployeeId,
    ) -> bool:
        """
        Check whether an employee exists.
        """

        return self.employee_repository.employee_exists(
            employee_id
        )

    def list_active_employees(
        self,
    ) -> list[Employee]:
        """
        Return all active employees.
        """

        self.log_start("List Active Employees")

        employees = (
            self.employee_repository.list_active_employees()
        )

        self.log_success("List Active Employees")

        return employees

    def get_manager(
        self,
        employee_id: EmployeeId,
    ) -> Employee | None:
        """
        Return the reporting manager.
        """

        employee = self.get_employee(employee_id)

        if employee.manager_id is None:
            return None

        return self.get_employee(employee.manager_id)