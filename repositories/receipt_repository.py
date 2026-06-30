"""
Receipt Repository.
"""

from config.settings import settings
from models import Receipt
from repositories.base import BaseRepository


class ReceiptRepository(BaseRepository):
    def __init__(self):

        super().__init__(settings.dynamodb.receipts_table)

    def create(
        self,
        receipt: Receipt,
    ) -> None:

        self.put_item(receipt.to_dynamodb_item())

    def get_by_receipt_id(
        self,
        receipt_id: str,
    ) -> Receipt | None:

        item = self.get_item(
            "receipt_id",
            receipt_id,
        )

        if item is None:
            return None

        return Receipt.model_validate(item)
