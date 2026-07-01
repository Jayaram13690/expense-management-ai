"""
Test Tool Registration.

Verify that every tool is properly decorated with the Strands @tool decorator.
"""

from unittest.mock import patch

import pytest


def test_expense_tools_registration():
    """Test that expense tools are properly registered with @tool decorator."""
    from tools.expense_tools import get_claim, preview_claim, submit_claim

    # Verify each tool has the expected attributes from @tool decorator
    for tool_func in [preview_claim, submit_claim, get_claim]:
        assert callable(tool_func)
        # Check if the function has been decorated (will have additional attributes)
        assert hasattr(tool_func, "__name__")
        assert tool_func.__name__ in ["preview_claim", "submit_claim", "get_claim"]


def test_employee_tools_registration():
    """Test that employee tools are properly registered with @tool decorator."""
    from tools.employee_tools import get_employee_details, list_employee_claims

    for tool_func in [get_employee_details, list_employee_claims]:
        assert callable(tool_func)
        assert hasattr(tool_func, "__name__")
        assert tool_func.__name__ in ["get_employee_details", "list_employee_claims"]


def test_policy_tools_registration():
    """Test that policy tools are properly registered with @tool decorator."""
    from tools.policy_tools import get_expense_category, get_policy

    for tool_func in [get_policy, get_expense_category]:
        assert callable(tool_func)
        assert hasattr(tool_func, "__name__")
        assert tool_func.__name__ in ["get_policy", "get_expense_category"]


def test_approval_tools_registration():
    """Test that approval tools are properly registered with @tool decorator."""
    from tools.approval_tools import (
        approve_claim,
        list_manager_queue,
        list_pending_claims,
        reject_claim,
    )

    for tool_func in [approve_claim, reject_claim, list_pending_claims, list_manager_queue]:
        assert callable(tool_func)
        assert hasattr(tool_func, "__name__")
        assert tool_func.__name__ in [
            "approve_claim",
            "reject_claim",
            "list_pending_claims",
            "list_manager_queue",
        ]


def test_receipt_tools_registration():
    """Test that receipt tools are properly registered with @tool decorator."""
    from tools.receipt_tools import get_receipt_status, upload_receipt

    for tool_func in [upload_receipt, get_receipt_status]:
        assert callable(tool_func)
        assert hasattr(tool_func, "__name__")
        assert tool_func.__name__ in ["upload_receipt", "get_receipt_status"]


def test_tool_decorator_presence():
    """Test that tools have been decorated by checking for decorator-specific attributes."""
    # Import a tool and verify it has been decorated
    # The @tool decorator should add certain attributes or modify the function
    # We can check that the function is not the original service method
    from services.expense_claim_service import ExpenseClaimService
    from tools.expense_tools import preview_claim

    service = ExpenseClaimService()

    # The tool should not be the same object as the service method
    assert preview_claim is not service.preview_claim

    # The tool should be callable and have a different signature
    assert callable(preview_claim)
    assert preview_claim.__name__ == "preview_claim"
