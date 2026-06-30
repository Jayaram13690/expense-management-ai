"""
Receipt Repository.

Provides persistence operations for Receipt entities.
"""

from __future__ import annotations

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from config.settings import settings
from database.constants import (
    CLAIM_ID,
    CLAIM_INDEX,
    RECEIPT_ID,
)
from exceptions.repository import RepositoryException
from models.receipt import Receipt
from repositories.base import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    """
    Repository for Receipt entities.
    """

    def __init__(self) -> None:

        super().__init__(
            table_name=settings.dynamodb.receipts_table,
            partition_key=RECEIPT_ID,
            model_class=Receipt,
        )

    ###########################################################################
    # Receipt Queries
    ###########################################################################

    def get_receipt(
        self,
        receipt_id: str,
    ) -> Receipt | None:
        """
        Retrieve a receipt by identifier.
        """

        return self.get(receipt_id)

    def receipt_exists(
        self,
        receipt_id: str,
    ) -> bool:
        """
        Check whether a receipt exists.
        """

        return self.exists(receipt_id)

    def list_claim_receipts(
        self,
        claim_id: str,
    ) -> list[Receipt]:
        """
        Return every receipt belonging to a claim.
        """

        try:
            return self.query(
                IndexName=CLAIM_INDEX,
                KeyConditionExpression=Key(CLAIM_ID).eq(claim_id),
            )

        except ClientError as ex:
            raise RepositoryException(
                message=f"Unable to retrieve receipts for claim '{claim_id}'.",
                cause=ex,
            ) from ex

    def save(
        self,
        receipt: Receipt,
    ) -> Receipt:
        """
        Create or update a receipt.
        """

        if self.receipt_exists(receipt.receipt_id):
            return self.update(receipt)

        return self.create(receipt)

    def delete_receipt(
        self,
        receipt_id: str,
    ) -> None:
        """
        Delete a receipt.
        """

        self.delete(receipt_id)

    def count_claim_receipts(
        self,
        claim_id: str,
    ) -> int:
        """
        Return the number of receipts attached to a claim.
        """

        return len(self.list_claim_receipts(claim_id))
