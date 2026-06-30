"""
Database constants.

This module contains all reusable constants for DynamoDB.
Avoid hardcoding string literals throughout the database layer.
"""

from __future__ import annotations

###############################################################################
# DynamoDB Billing
###############################################################################

PAY_PER_REQUEST = "PAY_PER_REQUEST"

###############################################################################
# Attribute Types
###############################################################################

STRING = "S"

NUMBER = "N"

BOOLEAN = "BOOL"

MAP = "M"

LIST = "L"

###############################################################################
# Key Types
###############################################################################

HASH = "HASH"

RANGE = "RANGE"

###############################################################################
# Projection Types
###############################################################################

PROJECTION_ALL = "ALL"

PROJECTION_KEYS_ONLY = "KEYS_ONLY"

PROJECTION_INCLUDE = "INCLUDE"

###############################################################################
# DynamoDB Waiters
###############################################################################

TABLE_EXISTS_WAITER = "table_exists"

###############################################################################
# Server Side Encryption
###############################################################################

SSE_ENABLED = True

###############################################################################
# Point In Time Recovery
###############################################################################

PITR_ENABLED = True

###############################################################################
# Tag Keys
###############################################################################

PROJECT_TAG = "Project"

ENVIRONMENT_TAG = "Environment"

OWNER_TAG = "Owner"

###############################################################################
# Global Secondary Index Names
###############################################################################

EMAIL_INDEX = "email-index"

CATEGORY_CODE_INDEX = "category-code-index"

CATEGORY_GRADE_INDEX = "category-grade-index"

EMPLOYEE_SUBMISSION_INDEX = "employee-submission-index"

STATUS_SUBMISSION_INDEX = "status-submission-index"

APPROVER_STATUS_INDEX = "approver-status-index"

CLAIM_INDEX = "claim-index"

###############################################################################
# Attribute Names
###############################################################################

EMPLOYEE_ID = "employee_id"

EMAIL = "email"

CATEGORY_ID = "category_id"

CATEGORY_CODE = "category_code"

POLICY_ID = "policy_id"

EMPLOYEE_GRADE = "employee_grade"

CLAIM_ID = "claim_id"

CLAIM_STATUS = "claim_status"

APPROVER_ID = "approver_id"

SUBMISSION_DATE = "submission_date"

RECEIPT_ID = "receipt_id"

###############################################################################
# Table Status
###############################################################################

ACTIVE = "ACTIVE"

CREATING = "CREATING"

UPDATING = "UPDATING"

DELETING = "DELETING"
