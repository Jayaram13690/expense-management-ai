"""
Conversation Layer Package.

This package provides metadata for conversational interfaces in the Enterprise AI
Travel Expense Management System. It defines supported business intents, information
requirements, and reusable conversational prompts.

Design Principles:
-------------------
- Metadata only — no execution, routing, or business logic
- Lightweight and focused on conversational metadata
- Designed for consumption by future Coordinator Agents
- Clear separation from business layer, service layer, and tool layer
- No dependencies on services, repositories, tools, or agents

Package Contents:
-----------------
- intents: Business intents supported by the conversational interface
- requirements: Information requirements for each intent
- prompts: Reusable conversational questions for gathering information
"""

# Import core components
from conversation.intents import ConversationIntent

# Import commonly used prompts for convenience
from conversation.prompts import (  # Core conversational prompts; Additional useful prompts
    APPROVAL_REASON,
    APPROVER_ID,
    APPROVER_NAME,
    BUSINESS_PURPOSE,
    CLAIM_ID,
    COMMENTS,
    CONFIRM_APPROVAL,
    CONFIRM_REJECTION,
    CONFIRM_SUBMISSION,
    DATE_RANGE,
    DESTINATION,
    EMPLOYEE_ID,
    EXPENSE_AMOUNT,
    EXPENSE_CATEGORY,
    EXPENSE_DATE,
    EXPENSE_ITEMS,
    RECEIPT_TYPE,
    RECEIPT_UPLOAD,
    REJECTION_REASON,
    TRIP_DATES,
    TRIP_NAME,
)
from conversation.requirements import (
    APPROVE_CLAIM_REQUIREMENTS,
    GET_EMPLOYEE_DETAILS_REQUIREMENTS,
    GET_EXPENSE_CATEGORY_REQUIREMENTS,
    GET_EXPENSE_CLAIM_REQUIREMENTS,
    GET_POLICY_REQUIREMENTS,
    GET_RECEIPT_STATUS_REQUIREMENTS,
    LIST_EMPLOYEE_CLAIMS_REQUIREMENTS,
    LIST_MANAGER_QUEUE_REQUIREMENTS,
    LIST_PENDING_CLAIMS_REQUIREMENTS,
    PREVIEW_EXPENSE_CLAIM_REQUIREMENTS,
    REJECT_CLAIM_REQUIREMENTS,
    SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
    UNKNOWN_REQUIREMENTS,
    UPLOAD_RECEIPT_REQUIREMENTS,
    IntentRequirements,
)

__all__ = [
    # Core components
    "ConversationIntent",
    "IntentRequirements",
    # Intent requirements constants
    "SUBMIT_EXPENSE_CLAIM_REQUIREMENTS",
    "PREVIEW_EXPENSE_CLAIM_REQUIREMENTS",
    "GET_EXPENSE_CLAIM_REQUIREMENTS",
    "UPLOAD_RECEIPT_REQUIREMENTS",
    "GET_RECEIPT_STATUS_REQUIREMENTS",
    "APPROVE_CLAIM_REQUIREMENTS",
    "REJECT_CLAIM_REQUIREMENTS",
    "LIST_PENDING_CLAIMS_REQUIREMENTS",
    "LIST_MANAGER_QUEUE_REQUIREMENTS",
    "GET_EMPLOYEE_DETAILS_REQUIREMENTS",
    "LIST_EMPLOYEE_CLAIMS_REQUIREMENTS",
    "GET_POLICY_REQUIREMENTS",
    "GET_EXPENSE_CATEGORY_REQUIREMENTS",
    "UNKNOWN_REQUIREMENTS",
    # Commonly used conversational prompts
    "TRIP_NAME",
    "BUSINESS_PURPOSE",
    "DESTINATION",
    "TRIP_DATES",
    "EXPENSE_ITEMS",
    "EXPENSE_CATEGORY",
    "EXPENSE_AMOUNT",
    "EXPENSE_DATE",
    "RECEIPT_UPLOAD",
    "RECEIPT_TYPE",
    "CLAIM_ID",
    "EMPLOYEE_ID",
    "COMMENTS",
    "APPROVER_ID",
    "APPROVER_NAME",
    "APPROVAL_REASON",
    "REJECTION_REASON",
    "CONFIRM_SUBMISSION",
    "CONFIRM_APPROVAL",
    "CONFIRM_REJECTION",
    "DATE_RANGE",
]
