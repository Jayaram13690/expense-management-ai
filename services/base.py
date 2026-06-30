"""
Base service.

Provides common functionality shared by all business services.
"""

from __future__ import annotations

from utils.logger import get_logger


class BaseService:
    """
    Base class for all business services.
    """

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    def log_start(self, operation: str) -> None:
        """
        Log service operation start.
        """
        self.logger.info("Starting %s", operation)

    def log_success(self, operation: str) -> None:
        """
        Log successful operation.
        """
        self.logger.info("%s completed successfully.", operation)

    def log_failure(
        self,
        operation: str,
        message: str,
    ) -> None:
        """
        Log failed operation.
        """
        self.logger.error(
            "%s failed: %s",
            operation,
            message,
        )