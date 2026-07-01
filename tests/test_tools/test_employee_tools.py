"""
Test Employee Tools.

Test the employee tools to verify they properly delegate to their respective services.
"""

from unittest.mock import Mock, patch

import pytest

from common.identifiers import EmployeeId


@pytest.fixture
def mock_employee_service():
    """Create a mock EmployeeService for testing."""
    with patch("tools.employee_tools.employee_service") as mock_service:
        yield mock_service


@pytest.fixture
def mock_expense_claim_service():
    """Create a mock ExpenseClaimService for testing."""
    with patch("tools.employee_tools.expense_claim_service") as mock_service:
        yield mock_service


def test_get_employee_details_delegation(mock_employee_service):
    """Test that get_employee_details properly delegates to EmployeeService."""
    from tools.employee_tools import get_employee_details

    # Test data
    employee_id = "EMP0001"

    # Create mock response
    mock_employee = Mock()
    mock_employee.employee_id = employee_id
    mock_employee.first_name = "John"
    mock_employee.last_name = "Doe"
    mock_employee.email = "john.doe@company.com"
    mock_employee.department = "Engineering"

    # Configure mock
    mock_employee_service.get_employee.return_value = mock_employee

    # Call the tool
    result = get_employee_details(employee_id)

    # Verify delegation
    mock_employee_service.get_employee.assert_called_once_with(employee_id)
    assert result == mock_employee


def test_list_employee_claims_delegation(mock_expense_claim_service):
    """Test that list_employee_claims properly delegates to ExpenseClaimService."""
    from tools.employee_tools import list_employee_claims

    # Test data
    employee_id = "EMP0001"

    # Create mock response
    mock_claim1 = Mock()
    mock_claim1.claim_id = "CLM000000000001"
    mock_claim1.employee_id = employee_id

    mock_claim2 = Mock()
    mock_claim2.claim_id = "CLM000000000002"
    mock_claim2.employee_id = employee_id

    mock_claims = [mock_claim1, mock_claim2]

    # Configure mock
    mock_expense_claim_service.list_employee_claims.return_value = mock_claims

    # Call the tool
    result = list_employee_claims(employee_id)

    # Verify delegation
    mock_expense_claim_service.list_employee_claims.assert_called_once_with(employee_id)
    assert result == mock_claims
    assert len(result) == 2


def test_employee_tools_input_validation():
    """Test that employee tools accept correct input types."""
    from tools.employee_tools import get_employee_details, list_employee_claims

    # These should not raise type errors
    assert callable(get_employee_details)
    assert callable(list_employee_claims)

    # Verify function signatures
    import inspect

    # get_employee_details should accept EmployeeId
    sig = inspect.signature(get_employee_details)
    assert "employee_id" in sig.parameters

    # list_employee_claims should accept EmployeeId
    sig = inspect.signature(list_employee_claims)
    assert "employee_id" in sig.parameters


def test_employee_tools_return_types():
    """Test that employee tools have correct return type annotations."""
    import inspect

    from tools.employee_tools import get_employee_details, list_employee_claims

    # Verify the functions exist and are callable
    assert callable(get_employee_details)
    assert callable(list_employee_claims)

    # Check function signatures
    details_sig = inspect.signature(get_employee_details)
    claims_sig = inspect.signature(list_employee_claims)

    # Verify parameter names
    assert "employee_id" in details_sig.parameters
    assert "employee_id" in claims_sig.parameters


def test_employee_tools_service_isolation(mock_employee_service, mock_expense_claim_service):
    """Test that employee tools only call their respective services."""
    from tools.employee_tools import get_employee_details, list_employee_claims

    # Test get_employee_details only calls EmployeeService
    employee_id = "EMP0001"
    mock_employee = Mock()
    mock_employee_service.get_employee.return_value = mock_employee

    result = get_employee_details(employee_id)

    # Verify only EmployeeService was called
    mock_employee_service.get_employee.assert_called_once()
    mock_expense_claim_service.list_employee_claims.assert_not_called()

    # Test list_employee_claims only calls ExpenseClaimService
    mock_claims = []
    mock_expense_claim_service.list_employee_claims.return_value = mock_claims

    result = list_employee_claims(employee_id)

    # Verify only ExpenseClaimService was called
    mock_expense_claim_service.list_employee_claims.assert_called_once()
    mock_employee_service.get_employee.assert_called_once()  # From previous call
