"""
Expense Policy Repository.

Provides persistence operations for ExpensePolicy entities.
"""

from __future__ import annotations

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config.settings import settings
from database.constants import (
    CATEGORY_GRADE_INDEX,
    CATEGORY_ID,
    EMPLOYEE_GRADE,
    POLICY_ID,
)
from exceptions.repository import RepositoryException
from models.expense_policy import ExpensePolicy
from repositories.base import BaseRepository


class ExpensePolicyRepository(BaseRepository[ExpensePolicy]):
    """
    Repository for ExpensePolicy entities.
    """

    def __init__(self) -> None:

        super().__init__(
            table_name=settings.dynamodb.policies_table,
            partition_key=POLICY_ID,
            model_class=ExpensePolicy,
        )

    ###########################################################################
    # Policy Queries
    ###########################################################################

    def get_by_policy_id(
        self,
        policy_id: str,
    ) -> ExpensePolicy | None:
        """
        Retrieve a policy by its identifier.
        """

        return self.get(policy_id)

    def get_policy(
        self,
        *,
        category_id: str,
        employee_grade: str,
    ) -> ExpensePolicy | None:
        """
        Retrieve the policy applicable for a category and employee grade.
        """

        try:
            policies = self.query(
                IndexName=CATEGORY_GRADE_INDEX,
                KeyConditionExpression=(
                    Key(CATEGORY_ID).eq(category_id) & Key(EMPLOYEE_GRADE).eq(employee_grade)
                ),
                Limit=1,
            )

            if not policies:
                return None

            return policies[0]

        except ClientError as ex:
            raise RepositoryException(
                message=(
                    "Unable to retrieve expense policy "
                    f"for category '{category_id}' "
                    f"and grade '{employee_grade}'."
                ),
                cause=ex,
            ) from ex

    def list_policies_for_category(
        self,
        category_id: str,
    ) -> list[ExpensePolicy]:
        """
        Return every policy configured for a category.
        """

        try:
            return self.query(
                IndexName=CATEGORY_GRADE_INDEX,
                KeyConditionExpression=Key(CATEGORY_ID).eq(category_id),
            )

        except ClientError as ex:
            raise RepositoryException(
                message=f"Unable to list policies for '{category_id}'.",
                cause=ex,
            ) from ex

    def list_active_policies(
        self,
    ) -> list[ExpensePolicy]:
        """
        Return all active policies.
        """

        return [policy for policy in self.scan() if policy.is_active]

    def policy_exists(
        self,
        policy_id: str,
    ) -> bool:
        """
        Check whether a policy exists.
        """

        return self.exists(policy_id)
