"""
Expense Policy service.

Contains business operations related to expense reimbursement policies.
"""

from __future__ import annotations

from decimal import Decimal

from common.identifiers import CategoryId
from exceptions.repository import RepositoryException
from models.expense_policy import ExpensePolicy
from repositories.expense_policy_repository import (
    ExpensePolicyRepository,
)
from services.base import BaseService


class ExpensePolicyService(BaseService):
    """
    Expense Policy business service.
    """

    def __init__(self) -> None:
        super().__init__()

        self.policy_repository = ExpensePolicyRepository()

    ###########################################################################
    # Policy Operations
    ###########################################################################

    def get_policy(
        self,
        *,
        category_id: CategoryId,
        employee_grade: str,
    ) -> ExpensePolicy:
        """
        Retrieve the applicable expense policy.
        """

        self.log_start("Get Expense Policy")

        policy = self.policy_repository.get_policy(
            category_id=category_id,
            employee_grade=employee_grade,
        )

        if policy is None:

            self.log_failure(
                "Get Expense Policy",
                (
                    f"No policy configured for "
                    f"category '{category_id}' "
                    f"and grade '{employee_grade}'."
                ),
            )

            raise RepositoryException(
                message=(
                    f"No expense policy found for "
                    f"category '{category_id}' "
                    f"and grade '{employee_grade}'."
                )
            )

        self.log_success("Get Expense Policy")

        return policy

    def policy_exists(
        self,
        policy_id: str,
    ) -> bool:
        """
        Check whether a policy exists.
        """

        return self.policy_repository.policy_exists(
            policy_id
        )

    def list_active_policies(
        self,
    ) -> list[ExpensePolicy]:
        """
        Return every active policy.
        """

        self.log_start("List Active Policies")

        policies = (
            self.policy_repository.list_active_policies()
        )

        self.log_success("List Active Policies")

        return policies

    ###########################################################################
    # Business Rules
    ###########################################################################

    def get_daily_limit(
        self,
        *,
        category_id: CategoryId,
        employee_grade: str,
    ) -> Decimal:
        """
        Return the configured daily limit.
        """

        return self.get_policy(
            category_id=category_id,
            employee_grade=employee_grade,
        ).daily_limit

    def get_monthly_limit(
        self,
        *,
        category_id: CategoryId,
        employee_grade: str,
    ) -> Decimal:
        """
        Return the configured monthly limit.
        """

        return self.get_policy(
            category_id=category_id,
            employee_grade=employee_grade,
        ).monthly_limit

    def receipt_required(
        self,
        *,
        category_id: CategoryId,
        employee_grade: str,
    ) -> bool:
        """
        Determine whether receipt is mandatory.
        """

        return self.get_policy(
            category_id=category_id,
            employee_grade=employee_grade,
        ).receipt_required

    def approval_required(
        self,
        *,
        category_id: CategoryId,
        employee_grade: str,
    ) -> bool:
        """
        Determine whether manager approval is required.
        """

        return self.get_policy(
            category_id=category_id,
            employee_grade=employee_grade,
        ).approval_required

    def validate_daily_limit(
        self,
        *,
        amount: Decimal,
        category_id: CategoryId,
        employee_grade: str,
    ) -> bool:
        """
        Validate daily reimbursement limit.
        """

        return amount <= self.get_daily_limit(
            category_id=category_id,
            employee_grade=employee_grade,
        )

    def validate_monthly_limit(
        self,
        *,
        amount: Decimal,
        category_id: CategoryId,
        employee_grade: str,
    ) -> bool:
        """
        Validate monthly reimbursement limit.

        Note:
            This currently validates only the
            requested amount.

            Future versions will calculate
            cumulative monthly expenses.
        """

        return amount <= self.get_monthly_limit(
            category_id=category_id,
            employee_grade=employee_grade,
        )