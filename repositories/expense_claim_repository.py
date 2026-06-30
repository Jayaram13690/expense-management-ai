"""
Expense Claim Repository.
"""

from config.settings import settings
from models import ExpenseClaim
from repositories.base import BaseRepository


class ExpenseClaimRepository(BaseRepository):
    def __init__(self):

        super().__init__(settings.dynamodb.claims_table)

    def create(
        self,
        claim: ExpenseClaim,
    ) -> None:

        self.put_item(claim.to_dynamodb_item())

    def get_by_claim_id(
        self,
        claim_id: str,
    ) -> ExpenseClaim | None:

        item = self.get_item(
            "claim_id",
            claim_id,
        )

        if item is None:
            return None

        return ExpenseClaim.model_validate(item)
