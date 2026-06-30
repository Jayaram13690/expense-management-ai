"""
Employee Repository.
"""

from config.settings import settings
from models import Employee
from repositories.base import BaseRepository


class EmployeeRepository(BaseRepository):
    def __init__(self):

        super().__init__(settings.dynamodb.employees_table)

    def create(
        self,
        employee: Employee,
    ) -> None:

        self.put_item(employee.to_dynamodb_item())

    def get_by_employee_id(
        self,
        employee_id: str,
    ) -> Employee | None:

        item = self.get_item(
            "employee_id",
            employee_id,
        )

        if item is None:
            return None

        return Employee.model_validate(item)
