"""
Expense Category Repository.

Provides persistence operations for ExpenseCategory entities.
"""

from __future__ import annotations

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config.settings import settings
from database.constants import (
    CATEGORY_CODE,
    CATEGORY_CODE_INDEX,
    CATEGORY_ID,
)
from exceptions.repository import RepositoryException
from models.expense_category import ExpenseCategory
from repositories.base import BaseRepository


class ExpenseCategoryRepository(BaseRepository[ExpenseCategory]):
    """
    Repository for ExpenseCategory entities.
    """

    def __init__(self) -> None:

        super().__init__(
            table_name=settings.dynamodb.categories_table,
            partition_key=CATEGORY_ID,
            model_class=ExpenseCategory,
        )

    ###########################################################################
    # Category Queries
    ###########################################################################

    def get_by_category_id(
        self,
        category_id: str,
    ) -> ExpenseCategory | None:
        """
        Retrieve a category by its identifier.
        """

        return self.get(category_id)

    def get_by_category_code(
        self,
        category_code: str,
    ) -> ExpenseCategory | None:
        """
        Retrieve a category using the category_code GSI.
        """

        try:
            categories = self.query(
                IndexName=CATEGORY_CODE_INDEX,
                KeyConditionExpression=Key(CATEGORY_CODE).eq(category_code),
                Limit=1,
            )

            if not categories:
                return None

            return categories[0]

        except ClientError as ex:
            raise RepositoryException(
                message=f"Unable to retrieve category '{category_code}'.",
                cause=ex,
            ) from ex

    def category_exists(
        self,
        category_id: str,
    ) -> bool:
        """
        Determine whether a category exists.
        """

        return self.exists(category_id)

    def list_active_categories(
        self,
    ) -> list[ExpenseCategory]:
        """
        Return all active expense categories.
        """

        categories = self.scan()

        return [category for category in categories if category.is_active]

    def list_all_categories(
        self,
    ) -> list[ExpenseCategory]:
        """
        Return every expense category.
        """

        return self.scan()
