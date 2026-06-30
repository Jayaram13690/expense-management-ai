"""
Database health check.

Verifies that the DynamoDB infrastructure required by the
Enterprise AI Travel Expense Management System is available.

Execution:

    uv run python -m database.health
"""

from __future__ import annotations

from botocore.exceptions import ClientError

from config.settings import settings
from database.dynamodb import get_dynamodb_client
from database.utils import table_exists
from exceptions.database import DatabaseException
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseHealthChecker:
    """
    Performs health checks against DynamoDB.

    Responsibilities
    ----------------
    - Verify AWS connectivity
    - Verify required tables exist
    - Print health summary
    """

    def __init__(self) -> None:

        self.client = get_dynamodb_client()

        self.successful_checks: list[str] = []

        self.failed_checks: list[str] = []

    ###########################################################################
    # Public API
    ###########################################################################

    def run(self) -> bool:
        """
        Execute all health checks.

        Returns
        -------
        bool
            True if all checks pass.
        """

        logger.info("Running database health checks...")

        self.check_connection()

        self.check_required_tables()

        self.print_summary()

        return len(self.failed_checks) == 0

    ###########################################################################
    # Health Checks
    ###########################################################################

    def check_connection(self) -> None:
        """
        Verify DynamoDB connectivity.
        """

        try:
            self.client.list_tables()

            self.successful_checks.append("AWS DynamoDB Connection")

            logger.info("✓ AWS DynamoDB connection successful.")

        except ClientError as ex:
            self.failed_checks.append("AWS DynamoDB Connection")

            raise DatabaseException(
                message="Unable to connect to DynamoDB.",
                error_code="DB_CONNECTION_FAILED",
                cause=ex,
            ) from ex

    def check_required_tables(self) -> None:
        """
        Verify all required tables exist.
        """

        required_tables = [
            settings.dynamodb.employees_table,
            settings.dynamodb.categories_table,
            settings.dynamodb.policies_table,
            settings.dynamodb.claims_table,
            settings.dynamodb.receipts_table,
        ]

        for table_name in required_tables:
            if table_exists(self.client, table_name):
                logger.info("✓ %s", table_name)

                self.successful_checks.append(table_name)

            else:
                logger.error("✗ %s", table_name)

                self.failed_checks.append(table_name)

    ###########################################################################
    # Summary
    ###########################################################################

    def print_summary(self) -> None:

        logger.info("")

        logger.info("=" * 70)

        logger.info("DATABASE HEALTH REPORT")

        logger.info("=" * 70)

        logger.info("Successful Checks")

        for check in self.successful_checks:
            logger.info("  ✓ %s", check)

        logger.info("")

        logger.info("Failed Checks")

        if self.failed_checks:
            for check in self.failed_checks:
                logger.info("  ✗ %s", check)

        else:
            logger.info("  None")

        logger.info("")

        if self.failed_checks:
            logger.error("DATABASE STATUS : UNHEALTHY")

        else:
            logger.info("DATABASE STATUS : HEALTHY")

        logger.info("=" * 70)


def main() -> None:
    """
    Application entry point.
    """

    checker = DatabaseHealthChecker()

    checker.run()


if __name__ == "__main__":
    main()
