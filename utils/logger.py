"""
Enterprise Logging Framework.

This module provides a reusable, thread-safe logging system with Rich console
output, configurable log levels, and support for structured logging.
"""

import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

from config.enums import LogLevel
from config.settings import settings


class EnterpriseLogger:
    """Singleton logger factory for enterprise applications.

    This class implements the singleton pattern to ensure a single logger instance
    throughout the application. It provides a reusable logger with Rich console
    output and configurable log levels.

    Attributes:
        _instance: Class-level instance for singleton pattern
        _loggers: Dictionary to cache logger instances by name
        _console: Rich console instance for colored output
    """

    _instance: Optional["EnterpriseLogger"] = None
    _loggers: dict[str, logging.Logger] = {}

    def __new__(cls) -> "EnterpriseLogger":
        """Create or return the singleton instance.

        Returns:
            The singleton instance of EnterpriseLogger.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the logger factory with Rich console and custom theme."""
        # Custom theme for Rich console
        custom_theme = Theme(
            {
                "logging.level.debug": "dim cyan",
                "logging.level.info": "green",
                "logging.level.warning": "yellow",
                "logging.level.error": "bold red",
                "logging.level.critical": "bold white on red",
                "logging.time": "dim blue",
                "logging.name": "bold magenta",
                "logging.path": "dim",
            }
        )

        # Initialize Rich console
        self._console = Console(theme=custom_theme, force_terminal=True, width=120, highlight=False)

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger instance with the specified name.

        Args:
            name: Name of the logger (typically __name__ from calling module)

        Returns:
            Configured logger instance ready for use.
        """
        if name not in self._loggers:
            self._loggers[name] = self._create_logger(name)

        return self._loggers[name]

    def _create_logger(self, name: str) -> logging.Logger:
        """Create and configure a new logger instance.

        Args:
            name: Name of the logger

        Returns:
            Fully configured logger instance.
        """
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(self._get_log_level())

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # Create Rich handler
        rich_handler = RichHandler(
            console=self._console,
            show_time=True,
            show_path=False,
            log_time_format="[%Y-%m-%d %H:%M:%S]",
            markup=True,
            rich_tracebacks=True,
        )
        rich_handler.setLevel(self._get_log_level())

        # Create custom formatter
        formatter = self._create_formatter()
        rich_handler.setFormatter(formatter)

        # Add handler
        logger.addHandler(rich_handler)
        logger.propagate = False

        return logger

    def _create_formatter(self) -> logging.Formatter:
        """Create a custom log formatter.

        Returns:
            Configured formatter instance.
        """
        return logging.Formatter(fmt="%(message)s", datefmt="[%Y-%m-%d %H:%M:%S]")

    def _get_log_level(self) -> int:
        """Get the log level from settings.

        Returns:
            Log level as integer constant.
        """
        log_level_mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }

        return log_level_mapping.get(
            settings.logging.log_level,
            logging.INFO,  # Default to INFO if not configured
        )

    def update_log_level(self, log_level: LogLevel) -> None:
        """Update the log level for all loggers.

        Args:
            log_level: New log level to apply
        """
        level = self._get_log_level()
        for logger in self._loggers.values():
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)


# Singleton instance
_logger_factory = EnterpriseLogger()


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    This is the main entry point for obtaining logger instances throughout
    the application. It provides a thread-safe, singleton logger factory
    with Rich console output and configurable log levels.

    Args:
        name: Name of the logger (typically __name__ from calling module)

    Returns:
        Configured logger instance ready for use.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return _logger_factory.get_logger(name)
