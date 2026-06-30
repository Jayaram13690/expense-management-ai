"""
Base Repository.

Provides common CRUD functionality for all repositories.
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from botocore.exceptions import ClientError

from database import get_dynamodb_resource
from exceptions import DatabaseException
from utils.logger import get_logger


class BaseRepository(ABC):
    """
    Base repository.

    All repositories inherit from this class.
    """

    def __init__(self, table_name: str):

        self.logger = get_logger(self.__class__.__name__)

        self.table = get_dynamodb_resource().Table(table_name)

    def exists(
        self,
        partition_key: str,
        value: str,
    ) -> bool:
        """
        Check whether an item exists.
        """

        try:
            response = self.table.get_item(Key={partition_key: value})

            return "Item" in response

        except ClientError as ex:
            raise DatabaseException(
                message="Failed checking item existence.",
                error_code="DB_EXISTS_FAILED",
                cause=ex,
            ) from ex

    def put_item(
        self,
        item: dict[str, Any],
    ) -> None:
        """
        Store item.
        """

        try:
            self.table.put_item(Item=item)

        except ClientError as ex:
            raise DatabaseException(
                message="Unable to save item.",
                error_code="DB_PUT_FAILED",
                cause=ex,
            ) from ex

    def get_item(
        self,
        partition_key: str,
        value: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve item.
        """

        try:
            response = self.table.get_item(Key={partition_key: value})

            return response.get("Item")

        except ClientError as ex:
            raise DatabaseException(
                message="Unable to retrieve item.",
                error_code="DB_GET_FAILED",
                cause=ex,
            ) from ex

    def delete_item(
        self,
        partition_key: str,
        value: str,
    ) -> None:
        """
        Delete item.
        """

        try:
            self.table.delete_item(Key={partition_key: value})

        except ClientError as ex:
            raise DatabaseException(
                message="Unable to delete item.",
                error_code="DB_DELETE_FAILED",
                cause=ex,
            ) from ex
