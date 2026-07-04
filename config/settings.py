"""
Application configuration using Pydantic Settings.

This module provides a centralized configuration system that loads settings from
environment variables and validates them using Pydantic models.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.enums import Environment, LogLevel


class AWSSettings(BaseSettings):
    """AWS-specific configuration settings.

    Attributes:
        aws_region: AWS region where services are deployed
        bedrock_model_id: AWS Bedrock model identifier for AI services
    """

    aws_region: str = "us-east-1"
    bedrock_model_id: str = "global.amazon.nova-2-lite-v1:0"

    model_config = SettingsConfigDict(env_prefix="AWS_", extra="forbid")


class DynamoDBSettings(BaseSettings):
    """DynamoDB table configuration.

    Attributes:
        employees_table: Table for employee data
        policies_table: Table for company policies
        categories_table: Table for expense categories
        claims_table: Table for expense claims
        receipts_table: Table for receipt storage
    """

    employees_table: str = Field(
        default="expense-ai-employees",
        validation_alias="EMPLOYEES_TABLE",
    )
    policies_table: str = Field(
        default="expense-ai-expense-policies",
        validation_alias="EXPENSE_POLICIES_TABLE",
    )
    categories_table: str = Field(
        default="expense-ai-expense-categories",
        validation_alias="EXPENSE_CATEGORIES_TABLE",
    )
    claims_table: str = Field(
        default="expense-ai-expense-claims",
        validation_alias="EXPENSE_CLAIMS_TABLE",
    )
    receipts_table: str = Field(
        default="expense-ai-receipts",
        validation_alias="RECEIPTS_TABLE",
    )

    @field_validator(
        "employees_table", "policies_table", "categories_table", "claims_table", "receipts_table"
    )
    def validate_table_name(cls, v):
        """Validate that table names are not empty."""
        if not v or not v.strip():
            raise ValueError("Table name cannot be empty")
        return v

    model_config = SettingsConfigDict(env_prefix="DYNAMODB_", extra="forbid")


class LoggingSettings(BaseSettings):
    """Logging configuration.

    Attributes:
        log_level: Minimum log level for application logging
    """

    log_level: LogLevel = LogLevel.INFO

    model_config = SettingsConfigDict(env_prefix="LOGGING_", extra="forbid")


class WorkflowSettings(BaseSettings):
    """Workflow and processing configuration.

    Attributes:
        default_timeout: Default timeout for operations in seconds
        retry_count: Maximum number of retries for failed operations
        api_timeout: Timeout for API calls in seconds
        max_retry_count: Maximum number of retries for failed operations
        retry_backoff_factor: Multiplicative factor for retry backoff
    """

    default_timeout: int = 30
    retry_count: int = 3
    api_timeout: int = 30
    max_retry_count: int = 5
    retry_backoff_factor: float = 1.5

    @field_validator("default_timeout", "api_timeout")
    def validate_timeout(cls, v: int) -> int:
        """Validate that timeout values are positive."""
        if v <= 0:
            raise ValueError("Timeout must be greater than 0")
        return v

    @field_validator("retry_count", "max_retry_count")
    def validate_retry_count(cls, v: int) -> int:
        """Validate that retry count is non-negative."""
        if v < 0:
            raise ValueError("Retry count cannot be negative")
        return v

    @field_validator("retry_backoff_factor")
    def validate_backoff_factor(cls, v: int) -> int:
        """Validate that backoff factor is positive."""
        if v <= 0:
            raise ValueError("Retry backoff factor must be greater than 0")
        return v

    model_config = SettingsConfigDict(env_prefix="WORKFLOW_", extra="forbid")


class ReceiptUploadSettings(BaseSettings):
    """Receipt upload configuration."""

    s3_bucket: str = "expense-management-ai-receipts"
    max_file_size_mb: int = 10
    upload_retry_count: int = 1
    upload_timeout_seconds: int = 30

    @field_validator("s3_bucket")
    def validate_bucket_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("S3 bucket name cannot be empty")
        return v

    @field_validator("max_file_size_mb", "upload_timeout_seconds")
    def validate_positive_int(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Value must be greater than 0")
        return v

    @field_validator("upload_retry_count")
    def validate_retry_count(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Upload retry count cannot be negative")
        return v

    model_config = SettingsConfigDict(env_prefix="RECEIPT_UPLOAD_", extra="forbid")


class ApplicationSettings(BaseSettings):
    """Core application configuration.

    Attributes:
        application_name: Name of the application
        application_version: Current version of the application
        environment: Deployment environment
        debug: Debug mode flag
    """

    application_name: str = "Enterprise AI Travel Expense Management System"
    application_version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    @field_validator("application_name")
    def validate_application_name(cls, v):
        """Validate that application name is not empty."""
        if not v or not v.strip():
            raise ValueError("Application name cannot be empty")
        return v

    @field_validator("application_version")
    def validate_application_version(cls, v):
        """Validate that application version is not empty."""
        if not v or not v.strip():
            raise ValueError("Application version cannot be empty")
        return v

    model_config = SettingsConfigDict(env_prefix="APP_", extra="forbid")


class Settings(BaseSettings):
    """Main application settings container.

    This class aggregates all configuration settings into a single
    accessible object following the singleton pattern.

    Attributes:
        app: Application settings
        aws: AWS-specific settings
        dynamodb: DynamoDB table settings
        logging: Logging configuration
        workflow: Workflow and processing settings
    """

    app: ApplicationSettings = ApplicationSettings()
    aws: AWSSettings = AWSSettings()
    dynamodb: DynamoDBSettings = DynamoDBSettings()
    logging: LoggingSettings = LoggingSettings()
    workflow: WorkflowSettings = WorkflowSettings()
    receipt_upload: ReceiptUploadSettings = ReceiptUploadSettings()

    model_config = SettingsConfigDict(extra="forbid")

    @classmethod
    def load_from_env(cls):
        """Load settings from environment variables and .env file."""
        from dotenv import load_dotenv

        # Load environment variables from .env file
        load_dotenv()

        # Create settings instance
        settings = cls()
        return settings


# Singleton instance for global access
settings = Settings.load_from_env()


__all__ = ["settings", "Settings"]
