"""
Receipt service.

Contains business operations related to receipts.
"""

from __future__ import annotations

from common.identifiers import ClaimId, ReceiptId
from exceptions.repository import RepositoryException
from models.receipt import Receipt
from repositories.receipt_repository import ReceiptRepository
from services.base import BaseService


class ReceiptService(BaseService):
    """
    Receipt business service.
    """

    def __init__(self) -> None:
        super().__init__()

        self.receipt_repository = ReceiptRepository()

    ###########################################################################
    # Receipt Operations
    ###########################################################################

    def get_receipt(
        self,
        receipt_id: ReceiptId,
    ) -> Receipt:
        """
        Retrieve a receipt by identifier.
        """

        self.log_start("Get Receipt")

        receipt = self.receipt_repository.get_receipt(
            receipt_id
        )

        if receipt is None:

            self.log_failure(
                "Get Receipt",
                f"Receipt '{receipt_id}' does not exist.",
            )

            raise RepositoryException(
                message=f"Receipt '{receipt_id}' does not exist."
            )

        self.log_success("Get Receipt")

        return receipt

    def save_receipt(
        self,
        receipt: Receipt,
    ) -> Receipt:
        """
        Create or update a receipt.
        """

        self.log_start("Save Receipt")

        saved_receipt = self.receipt_repository.save(
            receipt
        )

        self.log_success("Save Receipt")

        return saved_receipt

    def delete_receipt(
        self,
        receipt_id: ReceiptId,
    ) -> None:
        """
        Delete a receipt.
        """

        self.log_start("Delete Receipt")

        self.receipt_repository.delete_receipt(
            receipt_id
        )

        self.log_success("Delete Receipt")

    ###########################################################################
    # Claim Receipt Operations
    ###########################################################################

    def get_claim_receipts(
        self,
        claim_id: ClaimId,
    ) -> list[Receipt]:
        """
        Return all receipts attached to a claim.
        """

        self.log_start("Get Claim Receipts")

        receipts = (
            self.receipt_repository.list_claim_receipts(
                claim_id
            )
        )

        self.log_success("Get Claim Receipts")

        return receipts

    def count_claim_receipts(
        self,
        claim_id: ClaimId,
    ) -> int:
        """
        Return the number of receipts attached to a claim.
        """

        return self.receipt_repository.count_claim_receipts(
            claim_id
        )

    def receipt_exists(
        self,
        receipt_id: ReceiptId,
    ) -> bool:
        """
        Check whether a receipt exists.
        """

        return self.receipt_repository.receipt_exists(
            receipt_id
        )