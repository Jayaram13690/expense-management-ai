"""
Field to Prompt Mappings.

This module defines the mapping between internal field names and conversational prompts.
These mappings are metadata that describe how to convert technical field names into
user-friendly questions.

Design Principles:
------------------
- Metadata only - no execution logic
- Part of the Conversation Layer
- Consumed by Coordinator for conversation management
- No dependencies on Coordinator, Agents, or Services
"""

from conversation.prompts import (
    APPROVER_ID,
    APPROVER_NAME,
    BUSINESS_PURPOSE,
    CLAIM_ID,
    COMMENTS,
    DESTINATION,
    EMPLOYEE_ID,
    EXPENSE_AMOUNT,
    EXPENSE_CATEGORY,
    EXPENSE_DATE,
    EXPENSE_DESCRIPTION,
    EXPENSE_ITEMS,
    MANAGER_ID,
    POLICY_CATEGORY,
    RECEIPT_NOTES,
    RECEIPT_TYPE,
    RECEIPT_UPLOAD,
    REJECTION_REASON,
    TRIP_END_DATE,
    TRIP_NAME,
    TRIP_START_DATE,
)

# Mapping of field names to prompt constants
FIELD_PROMPT_MAPPING = {
    # Employee fields
    "employee_id": EMPLOYEE_ID,
    # Trip fields
    "trip_name": TRIP_NAME,
    "business_purpose": BUSINESS_PURPOSE,
    "destination": DESTINATION,
    "trip_start_date": TRIP_START_DATE,
    "trip_end_date": TRIP_END_DATE,
    # Expense fields
    "expense_items": EXPENSE_ITEMS,
    "expense_category": EXPENSE_CATEGORY,
    "expense_amount": EXPENSE_AMOUNT,
    "expense_date": EXPENSE_DATE,
    "expense_description": EXPENSE_DESCRIPTION,
    # Claim fields
    "claim_id": CLAIM_ID,
    "comments": COMMENTS,
    # Receipt fields
    "receipt": RECEIPT_UPLOAD,
    "receipt_type": RECEIPT_TYPE,
    "receipt_id": CLAIM_ID,  # Reuse claim ID prompt for receipt ID
    "notes": RECEIPT_NOTES,
    # Approval fields
    "approver_id": APPROVER_ID,
    "approver_name": APPROVER_NAME,
    "approval_notes": COMMENTS,
    "reason": REJECTION_REASON,
    # Manager fields
    "manager_id": MANAGER_ID,
    # Policy fields
    "policy_category": POLICY_CATEGORY,
    "employee_grade": POLICY_CATEGORY,  # Reuse policy category for employee grade
}


def get_prompt_for_field(field_name: str) -> str | None:
    """Get the conversational prompt for a given field name."""
    return FIELD_PROMPT_MAPPING.get(field_name)


def has_prompt_for_field(field_name: str) -> bool:
    """Check if a prompt exists for the given field name."""
    return field_name in FIELD_PROMPT_MAPPING


__all__ = ["FIELD_PROMPT_MAPPING", "get_prompt_for_field", "has_prompt_for_field"]
