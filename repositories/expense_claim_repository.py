"""
Expense Claim Repository.

Provides persistence operations for ExpenseClaim entities.
"""

from __future__ import annotations

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config.settings import settings
from database.constants import (
    APPROVER_ID,
    APPROVER_STATUS_INDEX,
    CLAIM_ID,
    CLAIM_STATUS,
    EMPLOYEE_ID,
    EMPLOYEE_SUBMISSION_INDEX,
    STATUS_SUBMISSION_INDEX,
)
from exceptions.repository import RepositoryException
from models.expense_claim import ExpenseClaim
from repositories.base import BaseRepository


class ExpenseClaimRepository(BaseRepository[ExpenseClaim]):
    """
    Repository for ExpenseClaim entities.
    """

    def __init__(self) -> None:

        super().__init__(
            table_name=settings.dynamodb.claims_table,
            partition_key=CLAIM_ID,
            model_class=ExpenseClaim,
        )

    ###########################################################################
    # Basic Queries
    ###########################################################################

    def get_claim(
        self,
        claim_id: str,
    ) -> ExpenseClaim | None:
        """
        Retrieve a claim by identifier.
        """

        return self.get(claim_id)

    def claim_exists(
        self,
        claim_id: str,
    ) -> bool:
        """
        Check whether a claim exists.
        """

        return self.exists(claim_id)

    ###########################################################################
    # Employee Queries
    ###########################################################################

    def list_employee_claims(
        self,
        employee_id: str,
    ) -> list[ExpenseClaim]:
        """
        Return all claims submitted by an employee.
        Ordered by submission date.
        """

        try:
            return self.query(
                IndexName=EMPLOYEE_SUBMISSION_INDEX,
                KeyConditionExpression=Key(EMPLOYEE_ID).eq(employee_id),
                ScanIndexForward=False,
            )

        except ClientError as ex:
            raise RepositoryException(
                message=f"Unable to retrieve claims for employee '{employee_id}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Status Queries
    ###########################################################################

    def list_claims_by_status(
        self,
        status: str,
    ) -> list[ExpenseClaim]:
        """
        Return all claims with a specific status.
        Ordered by submission date.
        """

        try:
            return self.query(
                IndexName=STATUS_SUBMISSION_INDEX,
                KeyConditionExpression=Key(CLAIM_STATUS).eq(status),
                ScanIndexForward=False,
            )

        except ClientError as ex:
            raise RepositoryException(
                message=f"Unable to retrieve claims with status '{status}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Manager Queue
    ###########################################################################

    def list_manager_queue(
        self,
        approver_id: str,
        status: str,
    ) -> list[ExpenseClaim]:
        """
        Return all claims assigned to a manager.
        """

        try:
            return self.query(
                IndexName=APPROVER_STATUS_INDEX,
                KeyConditionExpression=(
                    Key(APPROVER_ID).eq(approver_id) & Key(CLAIM_STATUS).eq(status)
                ),
            )

        except ClientError as ex:
            raise RepositoryException(
                message=f"Unable to retrieve manager queue '{approver_id}'.",
                cause=ex,
            ) from ex

    ###########################################################################
    # Convenience Methods
    ###########################################################################

    def list_pending_claims(
        self,
    ) -> list[ExpenseClaim]:
        """
        Return every pending claim.
        """

        return self.list_claims_by_status("PENDING")

    def list_approved_claims(
        self,
    ) -> list[ExpenseClaim]:
        """
        Return every approved claim.
        """

        return self.list_claims_by_status("APPROVED")

    def list_rejected_claims(
        self,
    ) -> list[ExpenseClaim]:
        """
        Return every rejected claim.
        """

        return self.list_claims_by_status("REJECTED")

    ###########################################################################
    # Persistence Helpers
    ###########################################################################

    def save(
        self,
        claim: ExpenseClaim,
    ) -> ExpenseClaim:
        """
        Save a claim.

        New claims are created.
        Existing claims are updated.
        """

        if self.claim_exists(claim.claim_id):
            return self.update(claim)

        return self.create(claim)
