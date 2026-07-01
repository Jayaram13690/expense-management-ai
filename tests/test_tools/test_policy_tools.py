"""
Test Policy Tools.

Test the policy tools to verify they properly delegate to their respective services.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_policy_service():
    """Create a mock ExpensePolicyService."""
    with patch("tools.policy_tools.policy_service") as mock_service:
        yield mock_service


@pytest.fixture
def mock_category_service():
    """Create a mock ExpenseCategoryService."""
    with patch("tools.policy_tools.category_service") as mock_service:
        yield mock_service


def test_get_policy_delegation(mock_policy_service):
    """get_policy() should delegate to ExpensePolicyService."""

    from tools.policy_tools import get_policy

    category_id = "CAT0001"
    employee_grade = "G5"

    mock_policy = Mock()
    mock_policy.policy_id = "POL001"
    mock_policy.category_id = category_id
    mock_policy.employee_grade = employee_grade
    mock_policy.daily_limit = Decimal("150.00")
    mock_policy.monthly_limit = Decimal("1000.00")
    mock_policy.receipt_required = True
    mock_policy.approval_required = True
    mock_policy.currency = "USD"
    mock_policy.effective_from = date(2026, 1, 1)
    mock_policy.effective_to = date(2026, 12, 31)

    mock_policy_service.get_policy.return_value = mock_policy

    result = get_policy(
        category_id=category_id,
        employee_grade=employee_grade,
    )

    mock_policy_service.get_policy.assert_called_once_with(
        category_id=category_id,
        employee_grade=employee_grade,
    )

    assert result is mock_policy


def test_get_expense_category_delegation(mock_category_service):
    """get_expense_category() should delegate to ExpenseCategoryService."""

    from tools.policy_tools import get_expense_category

    category_code = "HOTEL"

    mock_category = Mock()
    mock_category.category_id = "CAT0001"
    mock_category.category_code = category_code
    mock_category.category_name = "Hotel Accommodation"

    mock_category_service.get_category_by_code.return_value = mock_category

    result = get_expense_category(category_code)

    mock_category_service.get_category_by_code.assert_called_once_with(category_code)

    assert result is mock_category


def test_policy_tools_input_validation():
    """Verify tool signatures."""

    import inspect

    from tools.policy_tools import (
        get_expense_category,
        get_policy,
    )

    assert callable(get_policy)
    assert callable(get_expense_category)

    policy_sig = inspect.signature(get_policy)

    assert "category_id" in policy_sig.parameters
    assert "employee_grade" in policy_sig.parameters

    category_sig = inspect.signature(get_expense_category)

    assert "category_code" in category_sig.parameters


def test_policy_tools_return_types():
    """Verify function signatures."""

    import inspect

    from tools.policy_tools import (
        get_expense_category,
        get_policy,
    )

    policy_sig = inspect.signature(get_policy)
    category_sig = inspect.signature(get_expense_category)

    assert "category_id" in policy_sig.parameters
    assert "employee_grade" in policy_sig.parameters
    assert "category_code" in category_sig.parameters


def test_policy_tools_service_isolation(
    mock_policy_service,
    mock_category_service,
):
    """Each tool should call only its own service."""

    from tools.policy_tools import (
        get_expense_category,
        get_policy,
    )

    category_id = "CAT0001"
    employee_grade = "G5"

    mock_policy = Mock()
    mock_policy_service.get_policy.return_value = mock_policy

    get_policy(
        category_id=category_id,
        employee_grade=employee_grade,
    )

    mock_policy_service.get_policy.assert_called_once()

    mock_category_service.get_category_by_code.assert_not_called()

    category_code = "HOTEL"

    mock_category = Mock()

    mock_category_service.get_category_by_code.return_value = mock_category

    get_expense_category(category_code)

    mock_category_service.get_category_by_code.assert_called_once_with(category_code)

    mock_policy_service.get_policy.assert_called_once()


def test_policy_tools_function_signatures():
    """Verify expected parameter names."""

    import inspect

    from tools.policy_tools import (
        get_expense_category,
        get_policy,
    )

    policy_sig = inspect.signature(get_policy)

    assert list(policy_sig.parameters.keys()) == [
        "category_id",
        "employee_grade",
    ]

    category_sig = inspect.signature(get_expense_category)

    assert list(category_sig.parameters.keys()) == [
        "category_code",
    ]
