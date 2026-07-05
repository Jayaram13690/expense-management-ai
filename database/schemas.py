"""
DynamoDB table schema definitions.

This module contains all DynamoDB table definitions used by the
Enterprise AI Travel Expense Management System.

No AWS calls should be made from this module.
Only schema definitions are stored here.
"""

from __future__ import annotations

from typing import Any

from config.settings import settings
from database.constants import (
    APPROVER_ID,
    APPROVER_STATUS_INDEX,
    CATEGORY_CODE,
    CATEGORY_CODE_INDEX,
    CATEGORY_GRADE_INDEX,
    CATEGORY_ID,
    CLAIM_BUSINESS_KEY,
    CLAIM_ID,
    CLAIM_INDEX,
    CLAIM_STATUS,
    EMAIL,
    EMAIL_INDEX,
    EMPLOYEE_GRADE,
    EMPLOYEE_ID,
    EMPLOYEE_SUBMISSION_INDEX,
    ENVIRONMENT_TAG,
    HASH,
    PAY_PER_REQUEST,
    POLICY_ID,
    PROJECT_TAG,
    PROJECTION_ALL,
    RANGE,
    RECEIPT_ID,
    SSE_ENABLED,
    STATUS_SUBMISSION_INDEX,
    STRING,
    SUBMISSION_DATE,
)


def _default_tags() -> list[dict[str, str]]:
    """
    Default tags applied to every DynamoDB table.
    """

    return [
        {
            "Key": PROJECT_TAG,
            "Value": settings.app.application_name,
        },
        {
            "Key": ENVIRONMENT_TAG,
            "Value": settings.app.environment.value,
        },
    ]


def employee_table_schema() -> dict[str, Any]:
    """
    Employees table schema.
    """

    return {
        "TableName": settings.dynamodb.employees_table,
        "BillingMode": PAY_PER_REQUEST,
        "AttributeDefinitions": [
            {
                "AttributeName": EMPLOYEE_ID,
                "AttributeType": STRING,
            },
            {
                "AttributeName": EMAIL,
                "AttributeType": STRING,
            },
        ],
        "KeySchema": [
            {
                "AttributeName": EMPLOYEE_ID,
                "KeyType": HASH,
            }
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": EMAIL_INDEX,
                "KeySchema": [
                    {
                        "AttributeName": EMAIL,
                        "KeyType": HASH,
                    }
                ],
                "Projection": {
                    "ProjectionType": PROJECTION_ALL,
                },
            }
        ],
        "SSESpecification": {
            "Enabled": SSE_ENABLED,
        },
        "Tags": _default_tags(),
    }


def expense_category_table_schema() -> dict[str, Any]:
    """
    Expense Categories table schema.
    """

    return {
        "TableName": settings.dynamodb.categories_table,
        "BillingMode": PAY_PER_REQUEST,
        "AttributeDefinitions": [
            {
                "AttributeName": CATEGORY_ID,
                "AttributeType": STRING,
            },
            {
                "AttributeName": CATEGORY_CODE,
                "AttributeType": STRING,
            },
        ],
        "KeySchema": [
            {
                "AttributeName": CATEGORY_ID,
                "KeyType": HASH,
            }
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": CATEGORY_CODE_INDEX,
                "KeySchema": [
                    {
                        "AttributeName": CATEGORY_CODE,
                        "KeyType": HASH,
                    }
                ],
                "Projection": {
                    "ProjectionType": PROJECTION_ALL,
                },
            }
        ],
        "SSESpecification": {
            "Enabled": SSE_ENABLED,
        },
        "Tags": _default_tags(),
    }


def expense_policy_table_schema() -> dict[str, Any]:
    """
    Expense Policies table schema.
    """

    return {
        "TableName": settings.dynamodb.policies_table,
        "BillingMode": PAY_PER_REQUEST,
        "AttributeDefinitions": [
            {
                "AttributeName": POLICY_ID,
                "AttributeType": STRING,
            },
            {
                "AttributeName": CATEGORY_ID,
                "AttributeType": STRING,
            },
            {
                "AttributeName": EMPLOYEE_GRADE,
                "AttributeType": STRING,
            },
        ],
        "KeySchema": [
            {
                "AttributeName": POLICY_ID,
                "KeyType": HASH,
            }
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": CATEGORY_GRADE_INDEX,
                "KeySchema": [
                    {
                        "AttributeName": CATEGORY_ID,
                        "KeyType": HASH,
                    },
                    {
                        "AttributeName": EMPLOYEE_GRADE,
                        "KeyType": RANGE,
                    },
                ],
                "Projection": {
                    "ProjectionType": PROJECTION_ALL,
                },
            }
        ],
        "SSESpecification": {
            "Enabled": SSE_ENABLED,
        },
        "Tags": _default_tags(),
    }


def expense_claim_table_schema() -> dict[str, Any]:
    """
    Expense Claims table schema.
    """

    return {
        "TableName": settings.dynamodb.claims_table,
        "BillingMode": PAY_PER_REQUEST,
        "AttributeDefinitions": [
            {
                "AttributeName": CLAIM_ID,
                "AttributeType": STRING,
            },
            {
                "AttributeName": EMPLOYEE_ID,
                "AttributeType": STRING,
            },
            {
                "AttributeName": CLAIM_STATUS,
                "AttributeType": STRING,
            },
            {
                "AttributeName": APPROVER_ID,
                "AttributeType": STRING,
            },
            {
                "AttributeName": SUBMISSION_DATE,
                "AttributeType": STRING,
            },
        ],
        "KeySchema": [
            {
                "AttributeName": CLAIM_ID,
                "KeyType": HASH,
            }
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": EMPLOYEE_SUBMISSION_INDEX,
                "KeySchema": [
                    {
                        "AttributeName": EMPLOYEE_ID,
                        "KeyType": HASH,
                    },
                    {
                        "AttributeName": SUBMISSION_DATE,
                        "KeyType": RANGE,
                    },
                ],
                "Projection": {
                    "ProjectionType": PROJECTION_ALL,
                },
            },
            {
                "IndexName": STATUS_SUBMISSION_INDEX,
                "KeySchema": [
                    {
                        "AttributeName": CLAIM_STATUS,
                        "KeyType": HASH,
                    },
                    {
                        "AttributeName": SUBMISSION_DATE,
                        "KeyType": RANGE,
                    },
                ],
                "Projection": {
                    "ProjectionType": PROJECTION_ALL,
                },
            },
            {
                "IndexName": APPROVER_STATUS_INDEX,
                "KeySchema": [
                    {
                        "AttributeName": APPROVER_ID,
                        "KeyType": HASH,
                    },
                    {
                        "AttributeName": CLAIM_STATUS,
                        "KeyType": RANGE,
                    },
                ],
                "Projection": {
                    "ProjectionType": PROJECTION_ALL,
                },
            },
        ],
        "SSESpecification": {
            "Enabled": SSE_ENABLED,
        },
        "Tags": _default_tags(),
    }


def claim_business_key_table_schema() -> dict[str, Any]:
    """
    Claim business key lock table schema.
    """

    return {
        "TableName": settings.dynamodb.claim_business_keys_table,
        "BillingMode": PAY_PER_REQUEST,
        "AttributeDefinitions": [
            {
                "AttributeName": CLAIM_BUSINESS_KEY,
                "AttributeType": STRING,
            },
        ],
        "KeySchema": [
            {
                "AttributeName": CLAIM_BUSINESS_KEY,
                "KeyType": HASH,
            }
        ],
        "SSESpecification": {
            "Enabled": SSE_ENABLED,
        },
        "Tags": _default_tags(),
    }


def receipt_table_schema() -> dict[str, Any]:
    """
    Receipts table schema.
    """

    return {
        "TableName": settings.dynamodb.receipts_table,
        "BillingMode": PAY_PER_REQUEST,
        "AttributeDefinitions": [
            {
                "AttributeName": RECEIPT_ID,
                "AttributeType": STRING,
            },
            {
                "AttributeName": CLAIM_ID,
                "AttributeType": STRING,
            },
        ],
        "KeySchema": [
            {
                "AttributeName": RECEIPT_ID,
                "KeyType": HASH,
            }
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": CLAIM_INDEX,
                "KeySchema": [
                    {
                        "AttributeName": CLAIM_ID,
                        "KeyType": HASH,
                    }
                ],
                "Projection": {
                    "ProjectionType": PROJECTION_ALL,
                },
            }
        ],
        "SSESpecification": {
            "Enabled": SSE_ENABLED,
        },
        "Tags": _default_tags(),
    }


###############################################################################
# Table Schema Builders
###############################################################################

TABLE_SCHEMAS = (
    employee_table_schema,
    expense_category_table_schema,
    expense_policy_table_schema,
    expense_claim_table_schema,
    claim_business_key_table_schema,
    receipt_table_schema,
)
