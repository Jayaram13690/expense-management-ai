"""
AWS Session Management.

This module provides a singleton AWS session for the application.

All AWS services (DynamoDB, Bedrock, S3, CloudWatch) must obtain
their boto3 session from this module.

Do not instantiate boto3.Session() anywhere else.
"""

from __future__ import annotations

from threading import Lock

import boto3
from boto3.session import Session

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AWSSessionManager:
    """
    Singleton AWS Session Manager.

    Creates a single boto3 Session instance that is shared across
    the entire application.
    """

    _instance: AWSSessionManager | None = None
    _lock = Lock()

    def __new__(cls) -> AWSSessionManager:
        """
        Thread-safe singleton implementation.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()

        return cls._instance

    def _initialize(self) -> None:
        """
        Initialize boto3 session.
        """

        logger.info("Initializing AWS session...")

        self._session = boto3.Session(
            region_name=settings.aws.aws_region,
        )

        logger.info(
            "AWS session initialized successfully.",
        )

    @property
    def session(self) -> Session:
        """
        Return boto3 session.
        """
        return self._session


aws_session = AWSSessionManager()


def get_aws_session() -> Session:
    """
    Return shared boto3 session.
    """
    return aws_session.session
