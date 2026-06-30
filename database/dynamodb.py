"""
DynamoDB Manager.

Provides centralized access to DynamoDB Resource and Client.
"""

from __future__ import annotations

from boto3.resources.base import ServiceResource
from botocore.client import BaseClient

from database.session import get_aws_session
from utils.logger import get_logger

logger = get_logger(__name__)


class DynamoDBManager:
    """
    Centralized DynamoDB Manager.

    Lazily creates both Resource and Client.
    """

    def __init__(self) -> None:

        session = get_aws_session()

        self._resource: ServiceResource = session.resource("dynamodb")

        self._client: BaseClient = session.client("dynamodb")

    @property
    def resource(self) -> ServiceResource:
        """
        Return DynamoDB resource.
        """
        return self._resource

    @property
    def client(self) -> BaseClient:
        """
        Return DynamoDB client.
        """
        return self._client


dynamodb = DynamoDBManager()


def get_dynamodb_resource() -> ServiceResource:
    return dynamodb.resource


def get_dynamodb_client() -> BaseClient:
    return dynamodb.client
