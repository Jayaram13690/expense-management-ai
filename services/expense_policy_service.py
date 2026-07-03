"""
Expense Policy service.

Contains business operations related to expense reimbursement policies.
"""

from __future__ import annotations

from decimal import Decimal

from exceptions.service import ServiceException
from models.expense_policy import ExpensePolicy
from repositories.expense_policy_repository import (
    ExpensePolicyRepository,
)
from services.base import BaseService
from services.expense_category_service import ExpenseCategoryService


class ExpensePolicyService(BaseService):
    """
    Expense Policy business service.
    """

    def __init__(self) -> None:
        super().__init__()

        self.policy_repository = ExpensePolicyRepository()
        self.category_service = ExpenseCategoryService()

    ###########################################################################
    # Policy Operations
    ###########################################################################

    def get_policy(
        self,
        *,
        category_id: str,
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

            raise ServiceException(
                message=(
                    f"No reimbursement policy found for category '{category_id}' "
                    f"and employee grade '{employee_grade}'."
                ),
                error_code="POLICY_NOT_FOUND"
            )

        self.log_success("Get Expense Policy")

        return policy

    def get_policy_by_identifier(
        self,
        *,
        category_identifier: str,
        employee_grade: str,
    ) -> ExpensePolicy:
        """
        Retrieve the applicable expense policy using flexible category identification.

        Delegates category resolution entirely to
        :meth:`~services.expense_category_service.ExpenseCategoryService.resolve_category`.
        The Category Service is the single source of truth for all identifier formats.

        Supports:
            - ``category_id``   — e.g. ``CAT0001``
            - ``category_code`` — e.g. ``HOTEL``, ``TAXI``, ``AIR``
            - ``category_name`` — e.g. ``Hotel``, ``Meals``, ``Hotel Accommodation``

        Args:
            category_identifier: Any supported category identifier.
            employee_grade: Grade of the employee.

        Returns:
            :class:`~models.expense_policy.ExpensePolicy` domain model.

        Raises:
            ServiceException: If the category cannot be resolved, or if no
                policy is configured for the resolved category and employee grade.
        """

        self.log_start("Get Expense Policy by Identifier")

        # Delegate all resolution to the Category Service.
        # ServiceException propagates naturally if the category is not found.
        category = self.category_service.resolve_category(category_identifier)

        policy = self.policy_repository.get_policy(
            category_id=category.category_id,
            employee_grade=employee_grade,
        )

        if policy is None:
            self.log_failure(
                "Get Expense Policy by Identifier",
                (
                    f"No policy configured for category '{category.category_name}' "
                    f"({category.category_id}) and grade '{employee_grade}'."
                ),
            )

            raise ServiceException(
                message=(
                    f"No reimbursement policy found for category "
                    f"'{category.category_name}' "
                    f"and employee grade '{employee_grade}'."
                ),
                error_code="POLICY_NOT_FOUND",
            )

        self.log_success("Get Expense Policy by Identifier")

        return policy

    def policy_exists(
        self,
        policy_id: str,
    ) -> bool:
        """
        Check whether a policy exists.
        """

        return self.policy_repository.policy_exists(policy_id)

    def list_active_policies(
        self,
    ) -> list[ExpensePolicy]:
        """
        Return every active policy.
        """

        self.log_start("List Active Policies")

        policies = self.policy_repository.list_active_policies()

        self.log_success("List Active Policies")

        return policies

    ###########################################################################
    # Business Rules
    ###########################################################################

    def get_daily_limit(
        self,
        *,
        category_identifier: str,
        employee_grade: str,
    ) -> Decimal:
        """
        Return the configured daily limit.
        """

        policy = self.get_policy_by_identifier(
            category_identifier=category_identifier,
            employee_grade=employee_grade,
        )

        return policy.daily_limit

    def get_monthly_limit(
        self,
        *,
        category_identifier: str,
        employee_grade: str,
    ) -> Decimal:
        """
        Return the configured monthly limit.
        """

        policy = self.get_policy_by_identifier(
            category_identifier=category_identifier,
            employee_grade=employee_grade,
        )

        return policy.monthly_limit

    def receipt_required(
        self,
        *,
        category_identifier: str,
        employee_grade: str,
    ) -> bool:
        """
        Determine whether receipt is mandatory.
        """

        policy = self.get_policy_by_identifier(
            category_identifier=category_identifier,
            employee_grade=employee_grade,
        )

        return policy.receipt_required

    def approval_required(
        self,
        *,
        category_identifier: str,
        employee_grade: str,
    ) -> bool:
        """
        Determine whether manager approval is required.
        """

        policy = self.get_policy_by_identifier(
            category_identifier=category_identifier,
            employee_grade=employee_grade,
        )

        return policy.approval_required

    def validate_daily_limit(
        self,
        *,
        amount: Decimal,
        category_identifier: str,
        employee_grade: str,
    ) -> bool:
        """
        Validate daily reimbursement limit.
        """

        daily_limit = self.get_daily_limit(
            category_identifier=category_identifier,
            employee_grade=employee_grade,
        )

        return amount <= daily_limit

    def validate_monthly_limit(
        self,
        *,
        amount: Decimal,
        category_identifier: str,
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

        monthly_limit = self.get_monthly_limit(
            category_identifier=category_identifier,
            employee_grade=employee_grade,
        )

        return amount <= monthly_limit

    def check_employee_eligibility(
        self,
        *,
        category_identifier: str,
        employee_grade: str,
    ) -> bool:
        """
        Check if employee is eligible for expense category.
        """

        self.log_start("Check Employee Eligibility")

        try:
            policy = self.get_policy_by_identifier(
                category_identifier=category_identifier,
                employee_grade=employee_grade,
            )

            eligibility = policy.employee_grade == employee_grade

            self.log_success("Check Employee Eligibility")

            return eligibility

        except ServiceException:
            self.log_failure(
                "Check Employee Eligibility",
                (
                    f"No policy found for category '{category_identifier}' "
                    f"and grade '{employee_grade}'."
                ),
            )

            return False

    def get_category_limits(
        self,
        *,
        category_identifier: str,
        employee_grade: str,
    ) -> dict:
        """
        Retrieve expense category limits.
        """

        self.log_start("Get Category Limits")

        try:
            policy = self.get_policy_by_identifier(
                category_identifier=category_identifier,
                employee_grade=employee_grade,
            )

            limits = {
                "daily_limit": policy.daily_limit,
                "monthly_limit": policy.monthly_limit,
                "receipt_required": policy.receipt_required,
                "approval_required": policy.approval_required,
            }

            self.log_success("Get Category Limits")

            return limits

        except ServiceException:
            self.log_failure(
                "Get Category Limits",
                (
                    f"Cannot retrieve limits for category '{category_identifier}' "
                    f"and grade '{employee_grade}'."
                ),
            )

            raise

    def get_reimbursement_rules(
        self,
        *,
        category_identifier: str,
        employee_grade: str,
    ) -> dict:
        """
        Retrieve reimbursement rules.
        """

        self.log_start("Get Reimbursement Rules")

        try:
            policy = self.get_policy_by_identifier(
                category_identifier=category_identifier,
                employee_grade=employee_grade,
            )

            rules = {
                "reimbursement_percentage": policy.reimbursement_percentage,
                "processing_time_days": policy.processing_time_days,
                "currency": policy.currency,
                "special_conditions": policy.special_conditions,
            }

            self.log_success("Get Reimbursement Rules")

            return rules

        except ServiceException:
            self.log_failure(
                "Get Reimbursement Rules",
                (
                    f"Cannot retrieve reimbursement rules for category '{category_identifier}' "
                    f"and grade '{employee_grade}'."
                ),
            )

            raise

