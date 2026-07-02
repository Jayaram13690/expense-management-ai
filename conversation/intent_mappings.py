"""
Intent to Requirements Mappings.

This module defines the mapping between ConversationIntents and their corresponding
IntentRequirements. This metadata describes what information is required for each
business operation.

Design Principles:
------------------
- Metadata only - no execution logic
- Part of the Conversation Layer
- Consumed by Coordinator for conversation management
- No dependencies on Coordinator, Agents, or Services
"""

from conversation.intents import ConversationIntent
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
    UPLOAD_RECEIPT_REQUIREMENTS,
    IntentRequirements,
)

# Mapping of intents to their requirements
INTENT_REQUIREMENTS_MAPPING = {
    ConversationIntent.SUBMIT_EXPENSE_CLAIM: SUBMIT_EXPENSE_CLAIM_REQUIREMENTS,
    ConversationIntent.PREVIEW_EXPENSE_CLAIM: PREVIEW_EXPENSE_CLAIM_REQUIREMENTS,
    ConversationIntent.GET_EXPENSE_CLAIM: GET_EXPENSE_CLAIM_REQUIREMENTS,
    ConversationIntent.UPLOAD_RECEIPT: UPLOAD_RECEIPT_REQUIREMENTS,
    ConversationIntent.GET_RECEIPT_STATUS: GET_RECEIPT_STATUS_REQUIREMENTS,
    ConversationIntent.APPROVE_CLAIM: APPROVE_CLAIM_REQUIREMENTS,
    ConversationIntent.REJECT_CLAIM: REJECT_CLAIM_REQUIREMENTS,
    ConversationIntent.LIST_PENDING_CLAIMS: LIST_PENDING_CLAIMS_REQUIREMENTS,
    ConversationIntent.LIST_MANAGER_QUEUE: LIST_MANAGER_QUEUE_REQUIREMENTS,
    ConversationIntent.GET_EMPLOYEE_DETAILS: GET_EMPLOYEE_DETAILS_REQUIREMENTS,
    ConversationIntent.LIST_EMPLOYEE_CLAIMS: LIST_EMPLOYEE_CLAIMS_REQUIREMENTS,
    ConversationIntent.GET_POLICY: GET_POLICY_REQUIREMENTS,
    ConversationIntent.GET_EXPENSE_CATEGORY: GET_EXPENSE_CATEGORY_REQUIREMENTS,
}


def get_requirements_for_intent(intent: ConversationIntent) -> IntentRequirements | None:
    """
    Get the IntentRequirements for the specified intent.

    Returns None for unknown intents to allow graceful handling.
    """
    return INTENT_REQUIREMENTS_MAPPING.get(intent)


__all__ = ["INTENT_REQUIREMENTS_MAPPING", "get_requirements_for_intent"]
