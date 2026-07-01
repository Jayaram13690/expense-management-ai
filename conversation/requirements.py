"""
Conversation Requirements.

This module defines the information requirements for each supported business intent.
These requirements describe what information is needed to fulfill each conversational
intent, without containing any business logic or validation.

Design Principles:
-------------------
- Metadata only — no validation, execution, or business logic
- Immutable data structures using frozen dataclasses
- Clear separation between required and optional fields
- Comprehensive coverage of all intents defined in intents.py
- Reusable model for consistent requirement representation
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from conversation.intents import ConversationIntent


@dataclass(frozen=True)
class IntentRequirements:
    """
    Immutable metadata describing the information requirements for a business intent.

    This class captures what information is needed to fulfill a specific conversational
    intent. It is used by Coordinator Agents to guide the conversation and ensure all
    necessary information is collected before invoking services.

    Attributes:
        intent:
            The business intent these requirements apply to.

        required_fields:
            Fields that must be provided to fulfill the intent, in the natural
            conversational order. These are typically business identifiers, mandatory
            data, or essential parameters for the operation.

        optional_fields:
            Fields that can optionally be provided to enhance the operation, in
            suggested conversational order. These may include additional context,
            comments, or supplementary data.

        confirmation_required:
            Whether the operation requires explicit user confirmation before
            proceeding (e.g., for destructive or financially significant actions).

        success_message:
            A concise, professional message to display when the operation completes
            successfully. Provides feedback and closure in conversational interfaces.
    """

    intent: ConversationIntent
    required_fields: Sequence[str]
    optional_fields: Sequence[str]
    confirmation_required: bool
    success_message: str


# Expense Claim Submission and Management Requirements
SUBMIT_EXPENSE_CLAIM_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.SUBMIT_EXPENSE_CLAIM,
    required_fields=(
        "employee_id",
        "trip_name",
        "business_purpose",
        "destination",
        "trip_start_date",
        "trip_end_date",
        "expense_items",
    ),
    optional_fields=(
        "comments",
        "receipts",
    ),
    confirmation_required=True,
    success_message="Expense claim submitted successfully.",
)

PREVIEW_EXPENSE_CLAIM_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.PREVIEW_EXPENSE_CLAIM,
    required_fields=(
        "employee_id",
        "trip_name",
        "business_purpose",
        "destination",
        "trip_start_date",
        "trip_end_date",
        "expense_items",
    ),
    optional_fields=("comments",),
    confirmation_required=False,
    success_message="Expense claim preview generated.",
)

GET_EXPENSE_CLAIM_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.GET_EXPENSE_CLAIM,
    required_fields=("claim_id",),
    optional_fields=(),
    confirmation_required=False,
    success_message="Expense claim details retrieved.",
)

# Receipt Operations Requirements
UPLOAD_RECEIPT_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.UPLOAD_RECEIPT,
    required_fields=(
        "claim_id",
        "receipt",
        "receipt_type",
    ),
    optional_fields=("notes",),
    confirmation_required=False,
    success_message="Receipt uploaded successfully.",
)

GET_RECEIPT_STATUS_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.GET_RECEIPT_STATUS,
    required_fields=("receipt_id",),
    optional_fields=(),
    confirmation_required=False,
    success_message="Receipt status retrieved.",
)

# Approval Workflow Requirements
APPROVE_CLAIM_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.APPROVE_CLAIM,
    required_fields=(
        "claim_id",
        "approver_id",
        "approver_name",
    ),
    optional_fields=("approval_notes",),
    confirmation_required=True,
    success_message="Expense claim approved successfully.",
)

REJECT_CLAIM_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.REJECT_CLAIM,
    required_fields=(
        "claim_id",
        "approver_id",
        "approver_name",
        "reason",
    ),
    optional_fields=("rejection_notes",),
    confirmation_required=True,
    success_message="Expense claim rejected.",
)

LIST_PENDING_CLAIMS_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.LIST_PENDING_CLAIMS,
    required_fields=(),
    optional_fields=(
        "department_filter",
        "date_range",
    ),
    confirmation_required=False,
    success_message="Pending expense claims retrieved.",
)

LIST_MANAGER_QUEUE_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.LIST_MANAGER_QUEUE,
    required_fields=("manager_id",),
    optional_fields=(
        "status_filter",
        "date_range",
    ),
    confirmation_required=False,
    success_message="Manager approval queue retrieved.",
)

# Employee Information Requirements
GET_EMPLOYEE_DETAILS_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.GET_EMPLOYEE_DETAILS,
    required_fields=("employee_id",),
    optional_fields=(),
    confirmation_required=False,
    success_message="Employee details retrieved.",
)

LIST_EMPLOYEE_CLAIMS_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.LIST_EMPLOYEE_CLAIMS,
    required_fields=("employee_id",),
    optional_fields=(
        "status_filter",
        "date_range",
    ),
    confirmation_required=False,
    success_message="Employee claims retrieved.",
)

# Policy and Category Information Requirements
GET_POLICY_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.GET_POLICY,
    required_fields=(
        "category_id",
        "employee_grade",
    ),
    optional_fields=(),
    confirmation_required=False,
    success_message="Expense policy retrieved.",
)

GET_EXPENSE_CATEGORY_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.GET_EXPENSE_CATEGORY,
    required_fields=("category_code",),
    optional_fields=(),
    confirmation_required=False,
    success_message="Expense category retrieved.",
)

# Unknown Intent Requirements
UNKNOWN_REQUIREMENTS = IntentRequirements(
    intent=ConversationIntent.UNKNOWN,
    required_fields=(),
    optional_fields=(),
    confirmation_required=False,
    success_message="Request not understood. How can I help you?",
)


__all__ = [
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
]
