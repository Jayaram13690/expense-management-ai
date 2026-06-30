"""
Database seed utility.

Seeds the application with master/reference data.

This operation is idempotent and can be safely executed multiple times.
"""

from __future__ import annotations

from database.seed_data import (
    EMPLOYEES,
    EXPENSE_CATEGORIES,
    EXPENSE_POLICIES,
)
from repositories.employee_repository import EmployeeRepository
from repositories.expense_category_repository import (
    ExpenseCategoryRepository,
)
from repositories.expense_policy_repository import (
    ExpensePolicyRepository,
)
from utils.logger import get_logger

logger = get_logger(__name__)

###############################################################################
# Seeder
###############################################################################


class DatabaseSeeder:
    """
    Seeds the application's master data.
    """

    def __init__(self) -> None:

        self.employee_repository = EmployeeRepository()

        self.category_repository = ExpenseCategoryRepository()

        self.policy_repository = ExpensePolicyRepository()

        self.created = 0

        self.skipped = 0

    ###########################################################################
    # Employees
    ###########################################################################

    def seed_employees(self) -> None:

        logger.info("Seeding employees...")

        for employee in EMPLOYEES:
            if self.employee_repository.employee_exists(employee.employee_id):
                self.skipped += 1

                continue

            self.employee_repository.create(employee)

            self.created += 1

    ###########################################################################
    # Categories
    ###########################################################################

    def seed_categories(self) -> None:

        logger.info("Seeding expense categories...")

        for category in EXPENSE_CATEGORIES:
            if self.category_repository.category_exists(category.category_id):
                self.skipped += 1

                continue

            self.category_repository.create(category)

            self.created += 1

    ###########################################################################
    # Policies
    ###########################################################################

    def seed_policies(self) -> None:

        logger.info("Seeding expense policies...")

        for policy in EXPENSE_POLICIES:
            if self.policy_repository.policy_exists(policy.policy_id):
                self.skipped += 1

                continue

            self.policy_repository.create(policy)

            self.created += 1

    ###########################################################################
    # Seed
    ###########################################################################

    def run(self) -> None:

        logger.info("Starting database seed...")

        self.seed_employees()

        self.seed_categories()

        self.seed_policies()

        logger.info("")

        logger.info("=" * 70)

        logger.info("DATABASE SEED SUMMARY")

        logger.info("=" * 70)

        logger.info("Created Records : %s", self.created)

        logger.info("Skipped Records : %s", self.skipped)

        logger.info("=" * 70)


###############################################################################
# Entry Point
###############################################################################


def main() -> None:

    DatabaseSeeder().run()


if __name__ == "__main__":
    main()
