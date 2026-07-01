#!/usr/bin/env python3
"""
Simple test script to verify tool functionality without Strands decorator issues.
"""

import sys
from unittest.mock import Mock, patch


def test_tool_imports():
    """Test that all tools can be imported successfully."""
    print("Testing tool imports...")

    try:
        # Test individual imports
        from tools.approval_tools import (
            approve_claim,
            list_manager_queue,
            list_pending_claims,
            reject_claim,
        )
        from tools.employee_tools import get_employee_details, list_employee_claims
        from tools.expense_tools import get_claim, preview_claim, submit_claim
        from tools.policy_tools import get_expense_category, get_policy
        from tools.receipt_tools import get_receipt_status, upload_receipt

        print("✅ All individual tool imports successful")

        # Test package import
        import tools

        assert hasattr(tools, "preview_claim")
        assert hasattr(tools, "get_employee_details")
        assert hasattr(tools, "get_policy")
        assert hasattr(tools, "approve_claim")
        assert hasattr(tools, "upload_receipt")

        print("✅ Package import successful")
        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_tool_delegation():
    """Test that tools properly delegate to services."""
    print("\nTesting tool delegation...")

    try:
        # Mock the service
        with patch("tools.expense_tools.expense_claim_service") as mock_service:
            mock_service.preview_claim.return_value = Mock()

            # Import after mocking to avoid Strands decorator issues
            from tools.expense_tools import preview_claim

            # Create a mock request
            mock_request = Mock()

            # Call the tool
            result = preview_claim(mock_request)

            # Verify delegation
            mock_service.preview_claim.assert_called_once_with(mock_request)
            print("✅ Tool delegation test passed")
            return True

    except Exception as e:
        print(f"❌ Delegation test failed: {e}")
        return False


def test_tool_signatures():
    """Test that tools have correct signatures."""
    print("\nTesting tool signatures...")

    try:
        import inspect

        from tools.employee_tools import get_employee_details

        # Test a few key tools
        from tools.expense_tools import get_claim, preview_claim

        # Check preview_claim signature
        sig = inspect.signature(preview_claim)
        assert "request" in sig.parameters
        print("✅ preview_claim signature correct")

        # Check get_claim signature
        sig = inspect.signature(get_claim)
        assert "claim_id" in sig.parameters
        print("✅ get_claim signature correct")

        # Check get_employee_details signature
        sig = inspect.signature(get_employee_details)
        assert "employee_id" in sig.parameters
        print("✅ get_employee_details signature correct")

        return True

    except Exception as e:
        print(f"❌ Signature test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Running simple tool tests...\n")

    tests = [
        test_tool_imports,
        test_tool_delegation,
        test_tool_signatures,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n{'=' * 50}")
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
