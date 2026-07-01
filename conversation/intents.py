"""
Conversation Intents.

This module defines the supported business intents for the Enterprise AI Travel
Expense Management System. These intents represent the conversational capabilities
that future Coordinator Agents will support.

Design Principles:
-------------------
- Metadata only — no execution, routing, or business logic
- StrEnum-based for type safety and string comparison compatibility
- Comprehensive coverage of all supported business operations
- Clear, descriptive intent names that match business terminology
"""

from enum import StrEnum


class ConversationIntent(StrEnum):
    """
    Enumeration of supported conversational business intents.

    Each intent represents a business capability supported by the application.

    This module defines conversational metadata only.

    Future orchestration layers may consume these intents when determining
    how to continue a conversation.
    """

    # Expense Claim Submission and Management
    SUBMIT_EXPENSE_CLAIM = "submit_expense_claim"
    PREVIEW_EXPENSE_CLAIM = "preview_expense_claim"
    GET_EXPENSE_CLAIM = "get_expense_claim"

    # Receipt Operations
    UPLOAD_RECEIPT = "upload_receipt"
    GET_RECEIPT_STATUS = "get_receipt_status"

    # Approval Workflow
    APPROVE_CLAIM = "approve_claim"
    REJECT_CLAIM = "reject_claim"
    LIST_PENDING_CLAIMS = "list_pending_claims"
    LIST_MANAGER_QUEUE = "list_manager_queue"

    # Employee Information
    GET_EMPLOYEE_DETAILS = "get_employee_details"
    LIST_EMPLOYEE_CLAIMS = "list_employee_claims"

    # Policy and Category Information
    GET_POLICY = "get_policy"
    GET_EXPENSE_CATEGORY = "get_expense_category"

    # Fallback for unsupported or unclear requests
    UNKNOWN = "unknown"


__all__ = ["ConversationIntent"]
