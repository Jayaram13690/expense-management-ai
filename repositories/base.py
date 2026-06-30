"""
Base repository implementation.

Provides generic CRUD operations for DynamoDB-backed repositories.

Every repository in the application should inherit from BaseRepository.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from botocore.exceptions import ClientError
from pydantic import BaseModel

from database.dynamodb import get_dynamodb_resource
from exceptions.repository import RepositoryException
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Generic DynamoDB repository.

    Responsibilities
    ----------------
    - Create
    - Read
    - Update
    - Delete
    - Exists
    - Scan
    - Query

    Child repositories should only implement
    business-specific query methods.
    """

    def __init__(
        self,
        *,
        table_name: str,
        partition_key: str,
        model_class: type[T],
    ) -> None:

        self.table_name = table_name

        self.partition_key = partition_key

        self.model_class = model_class

        self.resource = get_dynamodb_resource()

        self.table = self.resource.Table(table_name)

    ###########################################################################
    # Create
    ###########################################################################

    def create(
        self,
        entity: T,
    ) -> T:
        """
        Persist a new entity.
        """

        try:
            logger.info(
                "Creating entity in table '%s'.",
                self.table_name,
            )

            if hasattr(entity, "to_dynamodb_item"):
                item = entity.to_dynamodb_item()

            else:
                item = entity.model_dump(mode="python")

            self.table.put_item(
                Item=item,
            )

            return entity

        except ClientError as ex:
            raise RepositoryException(
                message=f"Failed creating entity in '{self.table_name}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Get
    ###########################################################################

    def get(
        self,
        partition_value: Any,
    ) -> T | None:
        """
        Retrieve an entity by primary key.
        """

        try:
            response = self.table.get_item(
                Key={
                    self.partition_key: partition_value,
                }
            )

            item = response.get("Item")

            if item is None:
                return None

            return self.model_class.from_dict(item)

        except ClientError as ex:
            raise RepositoryException(
                message=f"Failed reading from '{self.table_name}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Update
    ###########################################################################

    def update(
        self,
        entity: T,
    ) -> T:
        """
        Replace an existing entity.
        """

        try:
            logger.info(
                "Updating entity in '%s'.",
                self.table_name,
            )

            if hasattr(entity, "touch"):
                entity.touch()

            if hasattr(entity, "to_dynamodb_item"):
                item = entity.to_dynamodb_item()

            else:
                item = entity.model_dump(mode="python")

            self.table.put_item(
                Item=item,
            )

            return entity

        except ClientError as ex:
            raise RepositoryException(
                message=f"Failed updating '{self.table_name}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Delete
    ###########################################################################

    def delete(
        self,
        partition_value: Any,
    ) -> None:
        """
        Delete an entity.
        """

        try:
            logger.info(
                "Deleting entity from '%s'.",
                self.table_name,
            )

            self.table.delete_item(
                Key={
                    self.partition_key: partition_value,
                }
            )

        except ClientError as ex:
            raise RepositoryException(
                message=f"Failed deleting from '{self.table_name}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Exists
    ###########################################################################

    def exists(
        self,
        partition_value: Any,
    ) -> bool:
        """
        Determine whether an entity exists.
        """

        return self.get(partition_value) is not None

    ###########################################################################
    # Scan
    ###########################################################################

    def scan(self) -> list[T]:
        """
        Scan an entire table.
        """

        try:
            response = self.table.scan()

            items = response.get("Items", [])

            return [self.model_class.from_dict(item) for item in items]

        except ClientError as ex:
            raise RepositoryException(
                message=f"Failed scanning '{self.table_name}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Query
    ###########################################################################

    def query(
        self,
        **kwargs: Any,
    ) -> list[T]:
        """
        Execute a DynamoDB query.

        kwargs are forwarded directly to boto3.
        """

        try:
            response = self.table.query(
                **kwargs,
            )

            items = response.get("Items", [])

            return [self.model_class.from_dict(item) for item in items]

        except ClientError as ex:
            raise RepositoryException(
                message=f"Failed querying '{self.table_name}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Count
    ###########################################################################

    def count(self) -> int:
        """
        Return number of items.

        Intended for administration and diagnostics.
        """

        return len(self.scan())

    ###########################################################################
    # Batch Create
    ###########################################################################

    def batch_create(
        self,
        entities: list[T],
    ) -> None:
        """
        Persist multiple entities.
        """

        try:
            with self.table.batch_writer() as batch:
                for entity in entities:
                    if hasattr(entity, "to_dynamodb_item"):
                        batch.put_item(
                            Item=entity.to_dynamodb_item(),
                        )

                    else:
                        batch.put_item(
                            Item=entity.model_dump(mode="python"),
                        )

        except ClientError as ex:
            raise RepositoryException(
                message=f"Failed batch insert into '{self.table_name}'.",
                cause=ex,
            ) from ex
