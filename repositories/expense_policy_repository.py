"""
Expense Policy Repository.
"""

from config.settings import settings
from models import ExpensePolicy
from repositories.base import BaseRepository


class ExpensePolicyRepository(BaseRepository):
    def __init__(self):

        super().__init__(settings.dynamodb.policies_table)

    def create(
        self,
        policy: ExpensePolicy,
    ) -> None:

        self.put_item(policy.to_dynamodb_item())

    def get_by_policy_id(
        self,
        policy_id: str,
    ) -> ExpensePolicy | None:

        item = self.get_item(
            "policy_id",
            policy_id,
        )

        if item is None:
            return None

        return ExpensePolicy.model_validate(item)
