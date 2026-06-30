"""
Database table initialization.

Creates all DynamoDB tables required by the
Enterprise AI Travel Expense Management System.
"""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from database.dynamodb import get_dynamodb_client
from database.schemas import TABLE_SCHEMAS
from database.utils import (
    enable_point_in_time_recovery,
    print_database_summary,
    table_exists,
    wait_until_active,
)
from exceptions.database import DatabaseException
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseInitializer:
    """
    Responsible for creating all DynamoDB tables.

    Responsibilities
    ----------------
    - Create missing tables
    - Skip existing tables
    - Wait until ACTIVE
    - Enable PITR
    - Print execution summary
    """

    def __init__(self) -> None:

        self.client = get_dynamodb_client()

        self.created_tables: list[str] = []

        self.skipped_tables: list[str] = []

        self.failed_tables: list[str] = []

    ###########################################################################
    # Public API
    ###########################################################################

    def initialize(self) -> None:
        """
        Initialize every required DynamoDB table.
        """

        logger.info("Initializing database...")

        for schema_builder in TABLE_SCHEMAS:
            schema = schema_builder()

            self.create_table(schema)

        print_database_summary(
            created_tables=self.created_tables,
            skipped_tables=self.skipped_tables,
            failed_tables=self.failed_tables,
        )

    ###########################################################################
    # Table Creation
    ###########################################################################

    def create_table(
        self,
        schema: dict[str, Any],
    ) -> None:
        """
        Create a DynamoDB table from a schema definition.
        """

        table_name = schema["TableName"]

        if table_exists(
            self.client,
            table_name,
        ):
            logger.info(
                "Table '%s' already exists. Skipping.",
                table_name,
            )

            self.skipped_tables.append(table_name)

            return

        logger.info(
            "Creating table '%s'...",
            table_name,
        )

        try:
            self.client.create_table(**schema)

            wait_until_active(
                self.client,
                table_name,
            )

            enable_point_in_time_recovery(
                self.client,
                table_name,
            )

            self.created_tables.append(table_name)

            logger.info(
                "Successfully created '%s'.",
                table_name,
            )

        except ClientError as ex:
            self.failed_tables.append(table_name)

            raise DatabaseException(
                message=f"Failed creating table '{table_name}'.",
                error_code="DB_TABLE_CREATE_FAILED",
                cause=ex,
            ) from ex


def main() -> None:
    """
    Application entry point.
    """

    initializer = DatabaseInitializer()

    initializer.initialize()


if __name__ == "__main__":
    main()
