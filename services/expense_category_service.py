"""
Expense Category service.

Contains business operations related to expense categories.
"""

from __future__ import annotations

from common.identifiers import CategoryId
from exceptions.repository import RepositoryException
from models.expense_category import ExpenseCategory
from repositories.expense_category_repository import (
    ExpenseCategoryRepository,
)
from services.base import BaseService


class ExpenseCategoryService(BaseService):
    """
    Expense Category business service.
    """

    def __init__(self) -> None:
        super().__init__()

        self.category_repository = ExpenseCategoryRepository()

    ###########################################################################
    # Category Operations
    ###########################################################################

    def get_category(
        self,
        category_id: CategoryId,
    ) -> ExpenseCategory:
        """
        Retrieve a category.
        """

        self.log_start("Get Expense Category")

        category = self.category_repository.get_by_category_id(category_id)

        if category is None:
            self.log_failure(
                "Get Expense Category",
                f"Category '{category_id}' does not exist.",
            )

            raise RepositoryException(message=f"Category '{category_id}' does not exist.")

        self.log_success("Get Expense Category")

        return category

    def get_category_by_code(
        self,
        category_code: str,
    ) -> ExpenseCategory:
        """
        Retrieve category using category code.
        """

        self.log_start("Get Expense Category By Code")

        category = self.category_repository.get_by_category_code(category_code)

        if category is None:
            self.log_failure(
                "Get Expense Category By Code",
                f"Category '{category_code}' does not exist.",
            )

            raise RepositoryException(message=f"Category '{category_code}' does not exist.")

        self.log_success("Get Expense Category By Code")

        return category

    def category_exists(
        self,
        category_id: CategoryId,
    ) -> bool:
        """
        Check whether a category exists.
        """

        return self.category_repository.category_exists(category_id)

    def list_active_categories(
        self,
    ) -> list[ExpenseCategory]:
        """
        Return active expense categories.
        """

        self.log_start("List Active Categories")

        categories = self.category_repository.list_active_categories()

        self.log_success("List Active Categories")

        return categories

    def list_all_categories(
        self,
    ) -> list[ExpenseCategory]:
        """
        Return every expense category.
        """

        return self.category_repository.list_all_categories()

    ###########################################################################
    # Business Rules
    ###########################################################################

    def requires_receipt(
        self,
        category_id: CategoryId,
    ) -> bool:
        """
        Determine whether receipt is required.
        """

        return self.get_category(category_id).receipt_required

    def requires_manager_approval(
        self,
        category_id: CategoryId,
    ) -> bool:
        """
        Determine whether manager approval is required.
        """

        return self.get_category(category_id).manager_approval_required

    def reimbursement_allowed(
        self,
        category_id: CategoryId,
    ) -> bool:
        """
        Determine whether reimbursement is allowed.
        """

        return self.get_category(category_id).reimbursement_allowed
