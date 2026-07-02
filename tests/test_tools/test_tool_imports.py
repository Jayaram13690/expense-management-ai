"""
Test Tool Imports.

Verify that all tool modules import successfully and exports are correct.
"""


def test_tools_package_import():
    """Test that the tools package can be imported."""
    import tools

    assert tools is not None


def test_expense_tools_import():
    """Test that expense_tools module imports successfully."""
    from tools import expense_tools

    assert expense_tools is not None


def test_employee_tools_import():
    """Test that employee_tools module imports successfully."""
    from tools import employee_tools

    assert employee_tools is not None


def test_policy_tools_import():
    """Test that policy_tools module imports successfully."""
    from tools import policy_tools

    assert policy_tools is not None


def test_approval_tools_import():
    """Test that approval_tools module imports successfully."""
    from tools import approval_tools

    assert approval_tools is not None


def test_receipt_tools_import():
    """Test that receipt_tools module imports successfully."""
    from tools import receipt_tools

    assert receipt_tools is not None


def test_all_tools_exported():
    """Test that all tools are properly exported from tools package."""
    import tools

    # Expense Tools
    assert hasattr(tools, "preview_claim")
    assert hasattr(tools, "submit_claim")
    assert hasattr(tools, "get_claim")

    # Employee Tools
    assert hasattr(tools, "get_employee_details")
    assert hasattr(tools, "list_employee_claims")

    # Policy Tools
    assert hasattr(tools, "get_policy")
    assert hasattr(tools, "get_expense_category")

    # Approval Tools
    assert hasattr(tools, "approve_claim")
    assert hasattr(tools, "reject_claim")
    assert hasattr(tools, "list_pending_claims")
    assert hasattr(tools, "list_manager_queue")

    # Receipt Tools
    assert hasattr(tools, "upload_receipt")
    assert hasattr(tools, "get_receipt_status")


def test_tools_all_list():
    """Test that __all__ is defined and contains all expected tools."""
    import tools

    expected_tools = [
        # Expense Tools
        "preview_claim",
        "submit_claim",
        "get_claim",
        # Employee Tools
        "get_employee_details",
        "list_employee_claims",
        # Policy Tools
        "get_policy",
        "get_expense_category",
        # Approval Tools
        "approve_claim",
        "reject_claim",
        "list_pending_claims",
        "list_manager_queue",
        # Receipt Tools
        "upload_receipt",
        "get_receipt_status",
    ]

    assert hasattr(tools, "__all__")
    assert set(tools.__all__) == set(expected_tools)


def test_individual_tool_imports():
    """Test that each individual tool can be imported directly."""
    # Expense Tools
    from tools.expense_tools import get_claim, preview_claim, submit_claim

    assert callable(preview_claim)
    assert callable(submit_claim)
    assert callable(get_claim)

    # Employee Tools
    from tools.employee_tools import get_employee_details, list_employee_claims

    assert callable(get_employee_details)
    assert callable(list_employee_claims)

    # Policy Tools
    from tools.policy_tools import get_expense_category, get_policy

    assert callable(get_policy)
    assert callable(get_expense_category)

    # Approval Tools
    from tools.approval_tools import (
        approve_claim,
        list_manager_queue,
        list_pending_claims,
        reject_claim,
    )

    assert callable(approve_claim)
    assert callable(reject_claim)
    assert callable(list_pending_claims)
    assert callable(list_manager_queue)

    # Receipt Tools
    from tools.receipt_tools import get_receipt_status, upload_receipt

    assert callable(upload_receipt)
    assert callable(get_receipt_status)
