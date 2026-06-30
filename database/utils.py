"""
Database utility functions.

Reusable DynamoDB helper functions used throughout the
database layer.
"""

from __future__ import annotations

from botocore.exceptions import ClientError, WaiterError

from database.constants import (
    PITR_ENABLED,
    TABLE_EXISTS_WAITER,
)
from exceptions.database import DatabaseException
from utils.logger import get_logger

logger = get_logger(__name__)


def table_exists(
    client,
    table_name: str,
) -> bool:
    """
    Check whether a DynamoDB table exists.
    """

    try:
        client.describe_table(
            TableName=table_name,
        )

        return True

    except client.exceptions.ResourceNotFoundException:
        return False

    except ClientError as ex:
        raise DatabaseException(
            message=f"Unable to determine if table '{table_name}' exists.",
            error_code="DB_TABLE_EXISTS_FAILED",
            cause=ex,
        ) from ex


def wait_until_active(
    client,
    table_name: str,
) -> None:
    """
    Wait until the table becomes ACTIVE.
    """

    logger.info(
        "Waiting for '%s' to become ACTIVE...",
        table_name,
    )

    try:
        waiter = client.get_waiter(
            TABLE_EXISTS_WAITER,
        )

        waiter.wait(
            TableName=table_name,
        )

    except WaiterError as ex:
        raise DatabaseException(
            message=f"Timeout waiting for table '{table_name}'.",
            error_code="DB_TABLE_WAIT_FAILED",
            cause=ex,
        ) from ex


def enable_point_in_time_recovery(
    client,
    table_name: str,
) -> None:
    """
    Enable Point-In-Time Recovery.
    """

    try:
        client.update_continuous_backups(
            TableName=table_name,
            PointInTimeRecoverySpecification={
                "PointInTimeRecoveryEnabled": PITR_ENABLED,
            },
        )

        logger.info(
            "PITR enabled for '%s'.",
            table_name,
        )

    except ClientError as ex:
        logger.warning(
            "Unable to enable PITR for '%s'. %s",
            table_name,
            ex,
        )


def print_database_summary(
    *,
    created_tables: list[str],
    skipped_tables: list[str],
    failed_tables: list[str],
) -> None:
    """
    Print database initialization summary.
    """

    logger.info("")

    logger.info("=" * 70)

    logger.info("DATABASE INITIALIZATION SUMMARY")

    logger.info("=" * 70)

    logger.info("Created Tables")

    if created_tables:
        for table in created_tables:
            logger.info("  ✓ %s", table)

    else:
        logger.info("  None")

    logger.info("")

    logger.info("Skipped Tables")

    if skipped_tables:
        for table in skipped_tables:
            logger.info("  ✓ %s", table)

    else:
        logger.info("  None")

    logger.info("")

    logger.info("Failed Tables")

    if failed_tables:
        for table in failed_tables:
            logger.info("  ✗ %s", table)

    else:
        logger.info("  None")

    logger.info("=" * 70)
