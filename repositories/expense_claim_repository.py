"""
Expense Claim Repository.

Provides persistence operations for ExpenseClaim entities.

Extended with monthly allowance aggregation methods that calculate
cumulative approved amounts for a given employee, category, and
calendar month directly from the claims table.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from config.enums import ClaimStatus
from config.settings import settings
from database.constants import (
    APPROVER_ID,
    APPROVER_STATUS_INDEX,
    CLAIM_BUSINESS_KEY,
    CLAIM_ID,
    CLAIM_STATUS,
    EMPLOYEE_ID,
    EMPLOYEE_SUBMISSION_INDEX,
    STATUS_SUBMISSION_INDEX,
)
from database.dynamodb import get_dynamodb_client, get_dynamodb_resource
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
        self.business_key_table_name = settings.dynamodb.claim_business_keys_table
        self.business_key_table = get_dynamodb_resource().Table(self.business_key_table_name)
        self.client = get_dynamodb_client()
        self._serializer = TypeSerializer()

    ###########################################################################
    # Basic Queries
    ###########################################################################

    def get_claim(
        self,
        claim_id: str,
    ) -> ExpenseClaim | None:
        """Retrieve a claim by identifier."""

        return self.get(claim_id)

    def get_claim_by_business_key(self, business_key: str) -> ExpenseClaim | None:
        """Retrieve a claim using its deterministic business key."""

        try:
            response = self.business_key_table.get_item(
                Key={
                    CLAIM_BUSINESS_KEY: business_key,
                }
            )
            item = response.get("Item")
            if item is None:
                return None

            claim_id = item.get(CLAIM_ID)
            if not isinstance(claim_id, str) or not claim_id.strip():
                return None

            return self.get_claim(claim_id)
        except ClientError as ex:
            raise RepositoryException(
                message=(
                    f"Failed reading business key '{business_key}' "
                    f"from '{self.business_key_table_name}'."
                ),
                cause=ex,
            ) from ex

    def claim_exists(
        self,
        claim_id: str,
    ) -> bool:
        """Check whether a claim exists."""

        return self.exists(claim_id)

    ###########################################################################
    # Employee Queries
    ###########################################################################

    def list_employee_claims(
        self,
        employee_id: str,
    ) -> list[ExpenseClaim]:
        """Return all claims submitted by an employee."""

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
        """Return all claims with a specific status."""

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
        """Return all claims assigned to a manager."""

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
        return self.list_claims_by_status("PENDING")

    def list_approved_claims(
        self,
    ) -> list[ExpenseClaim]:
        return self.list_claims_by_status("APPROVED")

    def list_rejected_claims(
        self,
    ) -> list[ExpenseClaim]:
        return self.list_claims_by_status("REJECTED")

    ###########################################################################
    # Persistence Helpers
    ###########################################################################

    def save(
        self,
        claim: ExpenseClaim,
    ) -> ExpenseClaim:
        """Save a claim, enforcing deterministic uniqueness for new claims."""

        if self.claim_exists(claim.claim_id):
            return self.update(claim)

        return self.create_with_business_key(claim)

    def create_with_business_key(
        self,
        claim: ExpenseClaim,
    ) -> ExpenseClaim:
        """Create a new claim and reserve its business key atomically."""

        business_key = claim.business_key or ExpenseClaim.business_key_from_claim(claim)
        claim.business_key = business_key
        claim_item = claim.to_dynamodb_item()
        lock_item = {
            CLAIM_BUSINESS_KEY: business_key,
            CLAIM_ID: claim.claim_id,
            EMPLOYEE_ID: claim.employee_id,
            "created_at": datetime.now(UTC).isoformat(),
        }

        try:
            self.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.business_key_table_name,
                            "Item": self._serialize_item(lock_item),
                            "ConditionExpression": "attribute_not_exists(#business_key)",
                            "ExpressionAttributeNames": {
                                "#business_key": CLAIM_BUSINESS_KEY,
                            },
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": self._serialize_item(claim_item),
                            "ConditionExpression": "attribute_not_exists(#claim_id)",
                            "ExpressionAttributeNames": {
                                "#claim_id": CLAIM_ID,
                            },
                        }
                    },
                ]
            )
            return claim
        except ClientError as ex:
            if self._is_duplicate_business_key_error(ex):
                duplicate_claim = self.get_claim_by_business_key(business_key)
                raise RepositoryException(
                    message="Expense claim already exists for this employee and trip.",
                    error_code="CLAIM_ALREADY_EXISTS",
                    metadata={
                        "business_key": business_key,
                        "duplicate_claim": (
                            duplicate_claim.model_dump(mode="python")
                            if duplicate_claim is not None
                            else None
                        ),
                    },
                    cause=ex,
                ) from ex

            raise RepositoryException(
                message="Failed creating expense claim.",
                error_code="CLAIM_CREATE_FAILED",
                metadata={"business_key": business_key},
                cause=ex,
            ) from ex

    def _serialize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return {key: self._serializer.serialize(value) for key, value in item.items()}

    def _is_duplicate_business_key_error(self, ex: ClientError) -> bool:
        error = ex.response.get("Error", {})
        if error.get("Code") != "TransactionCanceledException":
            return False

        reasons = ex.response.get("CancellationReasons", [])
        if isinstance(reasons, list):
            for reason in reasons:
                if not isinstance(reason, dict):
                    continue
                if reason.get("Code") == "ConditionalCheckFailed":
                    return True

        message = str(error.get("Message") or "")
        return "ConditionalCheckFailed" in message

    ###########################################################################
    # Monthly Allowance Aggregation
    ###########################################################################

    def get_monthly_category_consumption(
        self,
        employee_id: str,
        category_code: str,
        year: int,
        month: int,
    ) -> Decimal:
        """
        Return the sum of approved_amount for APPROVED claims belonging to
        the given employee and category in the specified calendar month.

        Only APPROVED claims contribute to monthly consumption.
        DRAFT, PENDING, SUBMITTED, REJECTED, CANCELLED, and DELETED claims
        are excluded.

        The date window is computed as the first and last day of the given
        year/month.  Because submission_date is stored as an ISO-8601 string
        (e.g. "2026-07-15T10:30:00+00:00"), string comparison works correctly
        for range checks when the format is consistent.

        Parameters
        ----------
        employee_id:
            Employee whose claims should be aggregated.
        category_code:
            Expense category code to filter (e.g. HOTEL, MEALS).
        year:
            Four-digit calendar year.
        month:
            Calendar month (1-12).

        Returns
        -------
        Decimal
            Sum of approved amounts; Decimal("0.00") when there are none.
        """
        from calendar import monthrange

        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        # Fetch all APPROVED claims for this employee via the existing GSI
        try:
            approved_claims = self.query(
                IndexName="employee-submission-index",
                KeyConditionExpression=Key("employee_id").eq(employee_id),
                ScanIndexForward=False,
            )
        except ClientError as ex:
            raise RepositoryException(
                message=(
                    f"Unable to retrieve approved claims for employee '{employee_id}' "
                    f"while calculating monthly consumption."
                ),
                error_code="MONTHLY_CONSUMPTION_QUERY_FAILED",
                cause=ex,
            ) from ex

        total = Decimal("0.00")
        upper_code = category_code.strip().upper()

        for claim in approved_claims:
            # Only count APPROVED claims
            if claim.status != ClaimStatus.APPROVED:
                continue

            # Check submission date falls within the requested month
            if claim.submitted_at is None:
                continue

            # Convert to an aware date for comparison
            submitted_date = claim.submitted_at.date()
            if not (first_day <= submitted_date <= last_day):
                continue

            # Sum the approved_amount for matching line items
            for item in claim.expense_line_items:
                if item.category_code.strip().upper() == upper_code:
                    total += item.approved_amount

        return total

    def get_monthly_employee_consumption(
        self,
        employee_id: str,
        year: int,
        month: int,
    ) -> dict[str, Decimal]:
        """
        Return the sum of approved_amount grouped by category_code for all
        APPROVED claims belonging to the given employee in the specified
        calendar month.

        Only APPROVED claims contribute.  All other statuses are excluded.

        Parameters
        ----------
        employee_id:
            Employee whose claims should be aggregated.
        year:
            Four-digit calendar year.
        month:
            Calendar month (1-12).

        Returns
        -------
        dict[str, Decimal]
            Mapping of category_code (UPPER) -> total approved_amount.
            An empty dict is returned when no approved claims exist.
        """
        from calendar import monthrange

        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        try:
            all_claims = self.query(
                IndexName="employee-submission-index",
                KeyConditionExpression=Key("employee_id").eq(employee_id),
                ScanIndexForward=False,
            )
        except ClientError as ex:
            raise RepositoryException(
                message=(
                    f"Unable to retrieve claims for employee '{employee_id}' "
                    f"while calculating monthly employee consumption."
                ),
                error_code="MONTHLY_EMPLOYEE_CONSUMPTION_QUERY_FAILED",
                cause=ex,
            ) from ex

        consumption: dict[str, Decimal] = {}

        for claim in all_claims:
            if claim.status != ClaimStatus.APPROVED:
                continue

            if claim.submitted_at is None:
                continue

            submitted_date = claim.submitted_at.date()
            if not (first_day <= submitted_date <= last_day):
                continue

            for item in claim.expense_line_items:
                upper_code = item.category_code.strip().upper()
                consumption[upper_code] = (
                    consumption.get(upper_code, Decimal("0.00")) + item.approved_amount
                )

        return consumption


__all__ = ["ExpenseClaimRepository"]
