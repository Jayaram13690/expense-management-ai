"""
Tools package for the Enterprise AI Travel Expense Management System.

This package provides native Strands tools that delegate operations to the
business service layer. These tools are designed for use by AI agents.

Architecture:
    Agent → @tool → Service → Repository → DynamoDB

All tools are thin delegation layers that:
- Call exactly one service method
- Do not contain business logic
- Do not access repositories directly
- Use existing domain models and DTOs
- Follow Strands Agents SDK patterns
"""

# Approval Tools
from .approval_tools import (
    approve_claim,
    list_manager_queue,
    list_pending_claims,
    reject_claim,
)

# Employee Tools
from .employee_tools import (
    get_employee_details,
    list_employee_claims,
)

# Expense Tools
from .expense_tools import (
    get_claim,
    preview_claim,
    submit_claim,
)

# Policy Tools
from .policy_tools import (
    get_expense_category,
    get_policy,
)

# Receipt Tools
from .receipt_tools import (
    get_receipt_status,
    upload_receipt,
)

__all__ = [
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
