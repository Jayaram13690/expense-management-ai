"""
Expense Category service.

Contains business operations related to expense categories.
"""

from __future__ import annotations

import re

from exceptions.repository import RepositoryException
from exceptions.service import ServiceException
from models.expense_category import ExpenseCategory
from repositories.expense_category_repository import (
    ExpenseCategoryRepository,
)
from services.base import BaseService

# Pattern that matches internal category_id values (e.g. CAT0001, CAT00123)
_CATEGORY_ID_PATTERN = re.compile(r"^CAT\d{4,10}$", re.IGNORECASE)


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
        category_id: str,
    ) -> ExpenseCategory:
        """
        Retrieve a category by its internal category_id.
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

    def resolve_category(
        self,
        identifier: str,
    ) -> ExpenseCategory:
        """
        Resolve any category identifier to an ExpenseCategory.

        This is the single entry point for all category resolution.
        The Policy module must use this method instead of performing its
        own identifier matching.

        Resolution order
        ----------------
        1. ``category_id``   — matches ``CAT`` followed by 4-10 digits
                               (e.g. ``CAT0001``).  Resolved via GetItem.
        2. ``category_code`` — all-uppercase token, typically 2-20 characters
                               (e.g. ``HOTEL``, ``TAXI``).  Resolved via GSI query.
        3. ``category_name`` — everything else (e.g. ``Hotel``, ``Meals``,
                               ``Hotel Accommodation``).  Resolved via a single
                               table scan with a three-tier name match
                               (exact → case-insensitive → partial).

        Args:
            identifier: A category_id, category_code, or category_name.

        Returns:
            The resolved :class:`~models.expense_category.ExpenseCategory`.

        Raises:
            ServiceException: With ``error_code="CATEGORY_NOT_FOUND"`` when no
                category can be resolved from the supplied identifier.
        """

        self.log_start("Resolve Expense Category")

        category: ExpenseCategory | None = None

        # --- Strategy 1: category_id (e.g. CAT0001) ---
        if _CATEGORY_ID_PATTERN.match(identifier):
            try:
                category = self.category_repository.get_by_category_id(identifier.upper())
            except RepositoryException:
                category = None

        # --- Strategy 2: category_code (e.g. HOTEL, TAXI, AIR) ---
        #     Attempt when the identifier looks like an uppercase code or when
        #     strategy 1 found nothing.
        if category is None:
            try:
                category = self.category_repository.get_by_category_code(identifier.upper())
            except RepositoryException:
                category = None

        # --- Strategy 3: category_name (e.g. Hotel, Meals, Hotel Accommodation) ---
        if category is None:
            try:
                category = self.category_repository.get_by_category_name(identifier)
            except RepositoryException:
                category = None

        if category is None:
            self.log_failure(
                "Resolve Expense Category",
                f"No category found for identifier '{identifier}'.",
            )

            raise ServiceException(
                message=f"Expense category '{identifier}' was not found.",
                error_code="CATEGORY_NOT_FOUND",
            )

        self.log_success("Resolve Expense Category")

        return category

    def category_exists(
        self,
        category_id: str,
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
        category_id: str,
    ) -> bool:
        """
        Determine whether receipt is required.
        """

        return self.get_category(category_id).receipt_required

    def requires_manager_approval(
        self,
        category_id: str,
    ) -> bool:
        """
        Determine whether manager approval is required.
        """

        return self.get_category(category_id).manager_approval_required

    def reimbursement_allowed(
        self,
        category_id: str,
    ) -> bool:
        """
        Determine whether reimbursement is allowed.
        """

        return self.get_category(category_id).reimbursement_allowed
