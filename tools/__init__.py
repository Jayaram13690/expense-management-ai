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

# Allowance Tools
from .allowance_tools import (
    get_allowance_summary_tool,
    get_remaining_allowance_tool,
    validate_allowance_tool,
)
# Approval Tools
from .approval_tools import (
    approve_claim,
    get_approval_history,
    get_approval_status,
    list_manager_queue,
    list_pending_claims,
    reject_claim,
)

# Employee Tools
from .employee_tools import (
    get_employee_department,
    get_employee_details,
    get_employee_grade,
    get_employee_manager,
    list_employee_claims,
)

# Expense Tools
from .expense_tools import (
    calculate_reimbursement,
    calculate_variance,
    detect_duplicate_claims,
    get_claim,
    get_claim_status,
    preview_claim,
    submit_claim,
    validate_policy_compliance,
)

# Policy Tools
from .policy_tools import (
    check_employee_eligibility,
    get_category_limits,
    get_expense_category,
    get_policy_by_identifier,
    get_reimbursement_rules,
)

# Receipt Tools
from .receipt_tools import (
    generate_expense_breakdown,
    generate_expense_claim_summary,
    generate_policy_application_summary,
    generate_reimbursement_summary,
    generate_variance_report,
    get_receipt_status,
    upload_receipt,
)

__all__ = [
    # Expense Tools
    "preview_claim",
    "submit_claim",
    "get_claim",
    "validate_policy_compliance",
    "detect_duplicate_claims",
    "calculate_reimbursement",
    "calculate_variance",
    "get_claim_status",
    # Employee Tools
    "get_employee_details",
    "list_employee_claims",
    "get_employee_department",
    "get_employee_grade",
    "get_employee_manager",
    # Policy Tools
    "get_expense_category",
    "get_category_limits",
    "get_policy_by_identifier",
    "get_reimbursement_rules",
    "check_employee_eligibility",
    # Approval Tools
    "approve_claim",
    "reject_claim",
    "list_pending_claims",
    "list_manager_queue",
    "get_approval_history",
    "get_approval_status",
    # Allowance Tools
    "validate_allowance_tool",
    "get_remaining_allowance_tool",
    "get_allowance_summary_tool",
    # Receipt Tools
    "upload_receipt",
    "get_receipt_status",
    "generate_expense_breakdown",
    "generate_expense_claim_summary",
    "generate_policy_application_summary",
    "generate_reimbursement_summary",
    "generate_variance_report",
]
