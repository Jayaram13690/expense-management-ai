"""
Conversation Layer Package.

This package provides conversational metadata and orchestration components for
expense claim conversations.
"""

from conversation.conversation_context import ConversationContext
from conversation.conversation_state import ConversationState
from conversation.execution_patterns import (
    HumanInTheLoopExecution,
    ParallelExecution,
    SequentialExecution,
)
from conversation.execution_plan import ExecutionPattern, ExecutionPlan
from conversation.execution_planner import ExecutionPlanner
from conversation.intents import ConversationIntent
from conversation.orchestrator import ConversationOrchestrator
from conversation.prompts import (
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
    "ConversationContext",
    "ConversationState",
    "ConversationOrchestrator",
    "ExecutionPattern",
    "ExecutionPlan",
    "ExecutionPlanner",
    "SequentialExecution",
    "ParallelExecution",
    "HumanInTheLoopExecution",
    "ConversationIntent",
    "IntentRequirements",
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
