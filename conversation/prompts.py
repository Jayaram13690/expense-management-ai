"""
Conversation Prompts.

This module defines reusable conversational questions used to gather information
from users. These prompts are designed to be natural, user-friendly questions
that can be used by Coordinator Agents when collecting required information for
business operations.

Design Principles:
-------------------
- Metadata only — no business logic, routing, or execution
- Natural language questions that are clear and user-friendly
- Independent prompts that can be reused across different contexts
- No mention of internal implementation details (agents, services, tools)
- Short, focused questions that elicit specific information
- Consistent style and tone throughout
"""

# Trip Information Prompts
TRIP_NAME = "What is the name of your business trip?"
BUSINESS_PURPOSE = "What was the purpose of this business trip?"
DESTINATION = "What was your travel destination?"
TRIP_DATES = "What were your travel dates?"
TRIP_START_DATE = "What was the start date of your trip?"
TRIP_END_DATE = "What was the end date of your trip?"

# Expense Information Prompts
EXPENSE_ITEMS = "Please list the expenses you incurred."
EXPENSE_CATEGORY = "What category does this expense belong to?"
EXPENSE_AMOUNT = "What was the amount of this expense?"
EXPENSE_DATE = "When did you incur this expense?"
EXPENSE_DESCRIPTION = "Please provide a brief description of this expense."

# Receipt Information Prompts
RECEIPT_UPLOAD = "Please upload your receipt."
RECEIPT_TYPE = "What type of receipt is this?"
RECEIPT_NOTES = "Would you like to add any notes about this receipt?"

# Claim Information Prompts
CLAIM_ID = "What is the claim ID you're referring to?"
EMPLOYEE_ID = "What is your employee ID?"
COMMENTS = "Would you like to add any additional comments?"

# Approval Information Prompts
APPROVER_ID = "What is your approver ID?"
APPROVER_NAME = "What is your full name as the approver?"
APPROVAL_REASON = "Please provide the reason for approving this claim."
REJECTION_REASON = "Please provide the reason for rejecting this claim."

# Manager Information Prompts
MANAGER_ID = "What is your manager ID?"

# Employee Information Prompts
EMPLOYEE_DETAILS_REQUEST = "Which employee would you like information about?"

# Policy Information Prompts
POLICY_CATEGORY = "Which expense category are you interested in?"
EMPLOYEE_GRADE = "What is your employee grade?"

# Filter and Search Prompts
DATE_RANGE = "Would you like to specify a date range?"

# Confirmation Prompts
CONFIRM_SUBMISSION = "Are you ready to submit this expense claim?"
CONFIRM_APPROVAL = "Are you sure you want to approve this claim?"
CONFIRM_REJECTION = "Are you sure you want to reject this claim?"

# General Prompts
ADDITIONAL_NOTES = "Would you like to add any additional notes?"
MORE_INFORMATION = "Do you have any additional information to provide?"

# Help and Clarification Prompts
HOW_CAN_I_HELP = "How can I help you with your expense management?"
CLARIFY_REQUEST = "Could you please clarify your request?"

__all__ = [
    # Trip Information Prompts
    "TRIP_NAME",
    "BUSINESS_PURPOSE",
    "DESTINATION",
    "TRIP_DATES",
    "TRIP_START_DATE",
    "TRIP_END_DATE",
    # Expense Information Prompts
    "EXPENSE_ITEMS",
    "EXPENSE_CATEGORY",
    "EXPENSE_AMOUNT",
    "EXPENSE_DATE",
    "EXPENSE_DESCRIPTION",
    # Receipt Information Prompts
    "RECEIPT_UPLOAD",
    "RECEIPT_TYPE",
    "RECEIPT_NOTES",
    # Claim Information Prompts
    "CLAIM_ID",
    "EMPLOYEE_ID",
    "COMMENTS",
    # Approval Information Prompts
    "APPROVER_ID",
    "APPROVER_NAME",
    "APPROVAL_REASON",
    "REJECTION_REASON",
    # Manager Information Prompts
    "MANAGER_ID",
    # Employee Information Prompts
    "EMPLOYEE_DETAILS_REQUEST",
    # Policy Information Prompts
    "POLICY_CATEGORY",
    "EMPLOYEE_GRADE",
    # Filter and Search Prompts
    "DATE_RANGE",
    # Confirmation Prompts
    "CONFIRM_SUBMISSION",
    "CONFIRM_APPROVAL",
    "CONFIRM_REJECTION",
    # General Prompts
    "ADDITIONAL_NOTES",
    "MORE_INFORMATION",
    # Help and Clarification Prompts
    "HOW_CAN_I_HELP",
    "CLARIFY_REQUEST",
]
