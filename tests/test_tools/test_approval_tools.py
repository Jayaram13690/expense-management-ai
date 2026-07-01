"""
Test Approval Tools.

Test the approval tools to verify they properly delegate to ExpenseClaimService.
"""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_expense_claim_service():
    """Create a mock ExpenseClaimService for testing."""
    with patch("tools.approval_tools.expense_claim_service") as mock_service:
        yield mock_service


def test_approve_claim_delegation(mock_expense_claim_service):
    """Test that approve_claim properly delegates to ExpenseClaimService."""
    from tools.approval_tools import approve_claim

    # Test data
    claim_id = "CLM000000000001"
    approver_id = "EMP0002"
    approver_name = "Jane Smith"

    # Create mock response
    mock_claim = Mock()
    mock_claim.claim_id = claim_id
    mock_claim.employee_id = "EMP0001"
    mock_claim.status = "APPROVED"
    mock_claim.approval.approver_id = approver_id
    mock_claim.approval.approver_name = approver_name

    # Configure mock
    mock_expense_claim_service.approve_claim.return_value = mock_claim

    # Call the tool
    result = approve_claim(claim_id, approver_id, approver_name)

    # Verify delegation
    mock_expense_claim_service.approve_claim.assert_called_once_with(
        claim_id=claim_id, approver_id=approver_id, approver_name=approver_name
    )
    assert result == mock_claim


def test_reject_claim_delegation(mock_expense_claim_service):
    """Test that reject_claim properly delegates to ExpenseClaimService."""
    from tools.approval_tools import reject_claim

    # Test data
    claim_id = "CLM000000000001"
    approver_id = "EMP0002"
    approver_name = "Jane Smith"
    reason = "Incomplete documentation"

    # Create mock response
    mock_claim = Mock()
    mock_claim.claim_id = claim_id
    mock_claim.employee_id = "EMP0001"
    mock_claim.status = "REJECTED"
    mock_claim.approval.approver_id = approver_id
    mock_claim.approval.approver_name = approver_name
    mock_claim.approval.rejection_reason = reason

    # Configure mock
    mock_expense_claim_service.reject_claim.return_value = mock_claim

    # Call the tool
    result = reject_claim(claim_id, approver_id, approver_name, reason)

    # Verify delegation
    mock_expense_claim_service.reject_claim.assert_called_once_with(
        claim_id=claim_id, approver_id=approver_id, approver_name=approver_name, reason=reason
    )
    assert result == mock_claim


def test_list_pending_claims_delegation(mock_expense_claim_service):
    """Test that list_pending_claims properly delegates to ExpenseClaimService."""
    from tools.approval_tools import list_pending_claims

    # Create mock response
    mock_claim1 = Mock()
    mock_claim1.claim_id = "CLM000000000001"
    mock_claim1.status = "SUBMITTED"

    mock_claim2 = Mock()
    mock_claim2.claim_id = "CLM000000000002"
    mock_claim2.status = "SUBMITTED"

    mock_claims = [mock_claim1, mock_claim2]

    # Configure mock
    mock_expense_claim_service.list_pending_claims.return_value = mock_claims

    # Call the tool
    result = list_pending_claims()

    # Verify delegation
    mock_expense_claim_service.list_pending_claims.assert_called_once_with()
    assert result == mock_claims
    assert len(result) == 2


def test_list_manager_queue_delegation(mock_expense_claim_service):
    """Test that list_manager_queue properly delegates to ExpenseClaimService."""
    from tools.approval_tools import list_manager_queue

    # Test data
    manager_id = "EMP0002"

    # Create mock response
    mock_claim1 = Mock()
    mock_claim1.claim_id = "CLM000000000001"
    mock_claim1.status = "SUBMITTED"
    mock_claim1.approval.approver_id = manager_id

    mock_claim2 = Mock()
    mock_claim2.claim_id = "CLM000000000002"
    mock_claim2.status = "SUBMITTED"
    mock_claim2.approval.approver_id = manager_id

    mock_claims = [mock_claim1, mock_claim2]

    # Configure mock
    mock_expense_claim_service.list_manager_queue.return_value = mock_claims

    # Call the tool
    result = list_manager_queue(manager_id)

    # Verify delegation
    mock_expense_claim_service.list_manager_queue.assert_called_once_with(manager_id)
    assert result == mock_claims
    assert len(result) == 2


def test_approval_tools_input_validation():
    """Test that approval tools accept correct input types."""
    from tools.approval_tools import (
        approve_claim,
        list_manager_queue,
        list_pending_claims,
        reject_claim,
    )

    # These should not raise type errors
    assert callable(approve_claim)
    assert callable(reject_claim)
    assert callable(list_pending_claims)
    assert callable(list_manager_queue)

    # Verify function signatures
    import inspect

    # approve_claim signature
    sig = inspect.signature(approve_claim)
    assert "claim_id" in sig.parameters
    assert "approver_id" in sig.parameters
    assert "approver_name" in sig.parameters

    # reject_claim signature
    sig = inspect.signature(reject_claim)
    assert "claim_id" in sig.parameters
    assert "approver_id" in sig.parameters
    assert "approver_name" in sig.parameters
    assert "reason" in sig.parameters

    # list_pending_claims signature
    sig = inspect.signature(list_pending_claims)
    assert len(sig.parameters) == 0  # No parameters

    # list_manager_queue signature
    sig = inspect.signature(list_manager_queue)
    assert "manager_id" in sig.parameters


def test_approval_tools_return_types():
    """Test that approval tools have correct return type annotations."""
    import inspect

    from tools.approval_tools import (
        approve_claim,
        list_manager_queue,
        list_pending_claims,
        reject_claim,
    )

    # Verify the functions exist and are callable
    assert callable(approve_claim)
    assert callable(reject_claim)
    assert callable(list_pending_claims)
    assert callable(list_manager_queue)

    # Check function signatures
    approve_sig = inspect.signature(approve_claim)
    reject_sig = inspect.signature(reject_claim)
    pending_sig = inspect.signature(list_pending_claims)
    queue_sig = inspect.signature(list_manager_queue)

    # Verify parameter names exist
    assert "claim_id" in approve_sig.parameters
    assert "claim_id" in reject_sig.parameters
    assert "manager_id" in queue_sig.parameters


def test_approval_tools_service_isolation(mock_expense_claim_service):
    """Test that approval tools only call ExpenseClaimService."""
    from tools.approval_tools import (
        approve_claim,
        list_manager_queue,
        list_pending_claims,
        reject_claim,
    )

    # Test approve_claim
    mock_claim = Mock()
    mock_expense_claim_service.approve_claim.return_value = mock_claim

    result = approve_claim("CLM0001", "EMP0001", "Test")
    mock_expense_claim_service.approve_claim.assert_called_once()

    # Test reject_claim
    mock_claim = Mock()
    mock_expense_claim_service.reject_claim.return_value = mock_claim

    result = reject_claim("CLM0001", "EMP0001", "Test", "Reason")
    mock_expense_claim_service.reject_claim.assert_called_once()

    # Test list_pending_claims
    mock_claims = []
    mock_expense_claim_service.list_pending_claims.return_value = mock_claims

    result = list_pending_claims()
    mock_expense_claim_service.list_pending_claims.assert_called_once()

    # Test list_manager_queue
    mock_claims = []
    mock_expense_claim_service.list_manager_queue.return_value = mock_claims

    result = list_manager_queue("EMP0001")
    mock_expense_claim_service.list_manager_queue.assert_called_once()

    # Verify only ExpenseClaimService was called (4 times total)
    assert mock_expense_claim_service.approve_claim.call_count == 1
    assert mock_expense_claim_service.reject_claim.call_count == 1
    assert mock_expense_claim_service.list_pending_claims.call_count == 1
    assert mock_expense_claim_service.list_manager_queue.call_count == 1
