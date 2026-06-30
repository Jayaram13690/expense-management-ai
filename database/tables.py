"""
DynamoDB Table Access.

Provides typed access to application tables.
"""

from __future__ import annotations

# from boto3.resources.factory import dynamodb
from config.settings import settings
from database.dynamodb import get_dynamodb_resource


def get_employees_table():

    return get_dynamodb_resource().Table(settings.dynamodb.employees_table)


def get_expense_policies_table():

    return get_dynamodb_resource().Table(settings.dynamodb.policies_table)


def get_expense_claims_table():

    return get_dynamodb_resource().Table(settings.dynamodb.claims_table)


def get_receipts_table():

    return get_dynamodb_resource().Table(settings.dynamodb.receipts_table)
